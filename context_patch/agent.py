"""
Context Patch Agent
==================
作为 Sub Agent 运行的版本上下文提取器

使用方法:
    from context_patch.agent import ContextPatchAgent
    
    agent = ContextPatchAgent()
    response = agent.execute(project_root="/path/to/project", format="compact")
    print(response.context_patch)
"""

import os
import re
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 知识库模块
try:
    from context_patch.knowledge import KnowledgeBase
    KNOWLEDGE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_AVAILABLE = False


@dataclass
class Dependency:
    """单个依赖项"""
    name: str
    version: str
    source: str
    type: str


@dataclass
class Project:
    """项目信息"""
    name: str
    path: str
    language: str
    framework: str
    node_version: Optional[str] = None
    python_version: Optional[str] = None
    java_version: Optional[str] = None
    dependencies: List[Dependency] = field(default_factory=list)


@dataclass
class AgentRequest:
    """Agent 请求"""
    project_root: str
    scan_depth: int = 2
    include_locked: bool = True
    format: str = "markdown"  # markdown, json, compact
    # 知识库相关参数
    enable_knowledge: bool = True  # 是否启用知识库
    knowledge_max_results: int = 3  # 知识库返回结果数
    knowledge_config_path: Optional[str] = None  # 知识库配置路径


@dataclass
class AgentResponse:
    """Agent 响应"""
    success: bool
    context_patch: str = ""
    version_map: Dict[str, Any] = field(default_factory=dict)
    projects_found: List[str] = field(default_factory=list)
    knowledge_context: str = ""  # 知识库上下文
    knowledge_results: List[Dict[str, Any]] = field(default_factory=list)  # 知识库检索结果
    error: Optional[str] = None


class ContextPatchAgent:
    """
    Context Patch Sub Agent
    ======================
    专门负责提取项目环境版本的 Sub Agent
    
    解决的问题:
    - 大模型因组件版本迭代导致的不一致问题
    - 版本接口参数匹配问题
    - 最短最优路径带来的生成惯性
    
    Effective Context = (Current Env Versions) + (API Contracts) + (Domain-Specific Good Cases) - (Redundant Implementation Details)
    """
    
    # 支持的依赖文件类型
    DEPENDENCY_FILES = {
        'package.json': 'npm',
        'requirements.txt': 'pip',
        'pom.xml': 'maven',
        'go.mod': 'go',
        'Cargo.toml': 'rust',
    }
    
    LOCK_FILES = {
        'yarn.lock': 'yarn',
        'package-lock.json': 'npm',
        'Pipfile.lock': 'pipenv',
        'poetry.lock': 'poetry',
        'Gemfile.lock': 'bundler',
    }
    
    def __init__(self):
        self.name = "context-patch-agent"
        self.version = "1.0.0"
        self.description = "项目环境版本上下文提取器"
        self.capabilities = [
            "detect_project_language",
            "extract_dependencies",
            "get_runtime_versions",
            "generate_context_patch"
        ]
    
    # ==================== 核心执行方法 ====================
    
    def execute(self, project_root: str, **kwargs) -> AgentResponse:
        """
        执行 Agent 任务
        
        Args:
            project_root: 项目根目录路径
            **kwargs: 其他参数 (scan_depth, include_locked, format, enable_knowledge, knowledge_max_results, knowledge_config_path)
            
        Returns:
            AgentResponse: 包含上下文补丁的响应
        """
        request = AgentRequest(
            project_root=project_root,
            **{k: v for k, v in kwargs.items() if k in [
                'scan_depth', 'include_locked', 'format', 
                'enable_knowledge', 'knowledge_max_results', 'knowledge_config_path'
            ]}
        )
        
        try:
            root_path = Path(request.project_root).resolve()
            
            if not root_path.exists():
                return AgentResponse(
                    success=False,
                    error=f"Project not found: {request.project_root}"
                )
            
            # 1. 扫描项目
            projects = self._scan_projects(root_path, request.scan_depth)
            
            if not projects:
                return AgentResponse(
                    success=False,
                    error="No valid projects found in directory"
                )
            
            # 2. 提取依赖
            version_map = {}
            for project in projects:
                deps = self._extract_all_dependencies(project)
                project.dependencies = deps
                version_map[project.name] = {
                    'language': project.language,
                    'framework': project.framework,
                    'runtime': {
                        'node': project.node_version,
                        'python': project.python_version,
                        'java': project.java_version,
                    },
                    'dependencies': [asdict(d) for d in deps]
                }
            
            # 3. 生成上下文
            context_patch = self._generate_context(projects, request.format, request.include_locked)
            
            # 4. 知识库检索（可选）
            knowledge_context = ""
            knowledge_results = []
            if request.enable_knowledge and KNOWLEDGE_AVAILABLE:
                try:
                    knowledge_context, knowledge_results = self._retrieve_knowledge(
                        projects, 
                        request.knowledge_max_results,
                        request.knowledge_config_path
                    )
                    # 将知识库上下文附加到版本上下文后面
                    if knowledge_context:
                        context_patch += knowledge_context
                except Exception as e:
                    print(f"Warning: Knowledge base retrieval failed: {e}")
            
            return AgentResponse(
                success=True,
                context_patch=context_patch,
                version_map=version_map,
                projects_found=[p.name for p in projects],
                knowledge_context=knowledge_context,
                knowledge_results=knowledge_results
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                error=f"Execution failed: {str(e)}"
            )
    
    # ==================== 扫描方法 ====================
    
    def _scan_projects(self, root: Path, depth: int) -> List[Project]:
        """扫描项目目录"""
        projects = []
        
        for item in root.iterdir():
            if not item.is_dir():
                continue
            if item.name.startswith('.') or item.name in self._get_skip_dirs():
                continue
            
            project = self._create_project(item)
            if project:
                projects.append(project)
        
        return projects
    
    def _get_skip_dirs(self) -> set:
        """获取需要跳过的目录"""
        return {
            'node_modules', '__pycache__', '.git', 'dist', 'build',
            'target', 'venv', '.venv', 'env', '.env', 'vendor',
            'coverage', '.pytest_cache', 'migrations', 'uploads'
        }
    
    def _create_project(self, path: Path) -> Optional[Project]:
        """创建项目对象"""
        # 检测项目类型
        language, framework = self._detect_type(path)
        
        if language == 'Unknown':
            return None
        
        # 获取运行时版本
        runtime = self._get_runtime_versions(path)
        
        return Project(
            name=path.name,
            path=str(path),
            language=language,
            framework=framework,
            node_version=runtime.get('node'),
            python_version=runtime.get('python'),
            java_version=runtime.get('java'),
        )
    
    def _detect_type(self, path: Path) -> tuple[str, str]:
        """检测项目类型"""
        # JavaScript/TypeScript
        if (path / "package.json").exists():
            try:
                data = json.loads((path / "package.json").read_text(encoding='utf-8'))
                deps = data.get('dependencies', {})
                dev_deps = data.get('devDependencies', {})
                
                if 'vue' in deps:
                    return 'JavaScript', f"Vue {deps.get('vue', '').strip('^~')}"
                if 'react' in deps:
                    return 'JavaScript', f"React {deps.get('react', '').strip('^~')}"
                if 'next' in deps:
                    return 'JavaScript', f"Next.js {deps.get('next', '').strip('^~')}"
                if 'nuxt' in deps:
                    return 'JavaScript', f"Nuxt {deps.get('nuxt', '').strip('^~')}"
                
                return 'JavaScript', 'Unknown'
            except:
                return 'JavaScript', 'Unknown'
        
        # Python
        if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            if (path / "requirements.txt").exists():
                content = (path / "requirements.txt").read_text(encoding='utf-8').lower()
                if 'flask' in content:
                    return 'Python', 'Flask'
                if 'django' in content:
                    return 'Python', 'Django'
                if 'fastapi' in content:
                    return 'Python', 'FastAPI'
            return 'Python', 'Unknown'
        
        # Java
        if (path / "pom.xml").exists():
            return 'Java', 'Spring Boot'
        
        # Go
        if (path / "go.mod").exists():
            return 'Go', 'Unknown'
        
        # Rust
        if (path / "Cargo.toml").exists():
            return 'Rust', 'Unknown'
        
        return 'Unknown', 'Unknown'
    
    def _get_runtime_versions(self, path: Path) -> Dict[str, Optional[str]]:
        """获取运行时版本"""
        versions = {}
        
        # Node.js
        try:
            result = subprocess.run(
                ['node', '--version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                versions['node'] = result.stdout.strip()
        except:
            pass
        
        # Python
        try:
            result = subprocess.run(
                ['python3', '--version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                versions['python'] = result.stdout.strip().replace('Python ', 'v')
        except:
            pass
        
        # Java
        try:
            result = subprocess.run(
                ['java', '--version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                versions['java'] = result.stderr.split('\n')[0].strip()
        except:
            pass
        
        return versions
    
    # ==================== 依赖提取方法 ====================
    
    def _extract_all_dependencies(self, project: Project) -> List[Dependency]:
        """提取所有依赖"""
        deps = []
        project_path = Path(project.path)
        
        # 依赖文件
        for filename, pkg_manager in self.DEPENDENCY_FILES.items():
            if (project_path / filename).exists():
                deps.extend(self._parse_dependency_file(project_path / filename, pkg_manager, filename))
        
        # Lock 文件 (获取精确版本)
        for filename, pkg_manager in self.LOCK_FILES.items():
            if (project_path / filename).exists():
                deps.extend(self._parse_lock_file(project_path / filename, pkg_manager))
        
        return deps
    
    def _parse_dependency_file(self, filepath: Path, pkg_manager: str, source: str) -> List[Dependency]:
        """解析依赖文件"""
        deps = []
        
        try:
            if pkg_manager == 'npm':
                data = json.loads(filepath.read_text(encoding='utf-8'))
                
                for name, version in data.get('dependencies', {}).items():
                    deps.append(Dependency(name=name, version=version, source=source, type='production'))
                
                for name, version in data.get('devDependencies', {}).items():
                    deps.append(Dependency(name=name, version=version, source=source, type='development'))
            
            elif pkg_manager == 'pip':
                content = filepath.read_text(encoding='utf-8')
                for line in content.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('-'):
                        continue
                    
                    match = re.match(r'^([a-zA-Z0-9_\-\.]+)([<>=!~]+.*)?$', line)
                    if match:
                        name = match.group(1)
                        version = match.group(2) or "latest"
                        deps.append(Dependency(name=name, version=version, source=source, type='runtime'))
            
            elif pkg_manager == 'maven':
                content = filepath.read_text(encoding='utf-8')
                
                # 提取 properties
                props = {}
                props_match = re.search(r'<properties>(.*?)</properties>', content, re.DOTALL)
                if props_match:
                    for m in re.finditer(r'<([^>]+)>([^<]+)</\1>', props_match.group(1)):
                        props[m.group(1)] = m.group(2)
                
                # 提取 dependencies
                for m in re.finditer(
                    r'<dependency>.*?<groupId>([^<]+)</groupId>.*?<artifactId>([^<]+)</artifactId>.*?(?:<version>([^<]+)</version>)?.*?</dependency>',
                    content, re.DOTALL
                ):
                    group_id, artifact_id, version = m.groups()
                    if version and version.startswith('${') and version.endswith('}'):
                        version = props.get(version[2:-1], version)
                    
                    name = f"{group_id}:{artifact_id}"
                    deps.append(Dependency(name=name, version=version or "inherited", source=source, type='runtime'))
        
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
        
        return deps
    
    def _parse_lock_file(self, filepath: Path, pkg_manager: str) -> List[Dependency]:
        """解析 lock 文件获取精确版本"""
        deps = []
        
        try:
            if pkg_manager in ['npm']:
                data = json.loads(filepath.read_text(encoding='utf-8'))
                
                def extract_deps(deps_dict):
                    for name, info in deps_dict.items():
                        if isinstance(info, dict) and 'version' in info:
                            deps.append(Dependency(
                                name=name,
                                version=info['version'],
                                source=filepath.name,
                                type='locked'
                            ))
                
                if 'dependencies' in data:
                    extract_deps(data['dependencies'])
            
            elif pkg_manager == 'yarn':
                content = filepath.read_text(encoding='utf-8')
                current_pkg = None
                
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if not line.startswith(' ') and ':' in line:
                            current_pkg = line.rstrip(':')
                        elif current_pkg and line.startswith('version "'):
                            version = line.split('"')[1]
                            deps.append(Dependency(
                                name=current_pkg,
                                version=version,
                                source=filepath.name,
                                type='locked'
                            ))
                            current_pkg = None
        
        except Exception as e:
            print(f"Error parsing lock file {filepath}: {e}")
        
        return deps
    
    # ==================== 上下文生成方法 ====================
    
    def _generate_context(self, projects: List[Project], format: str, include_locked: bool) -> str:
        """生成上下文补丁"""
        
        if format == "json":
            return self._generate_json_context(projects)
        elif format == "compact":
            return self._generate_compact_context(projects)
        else:
            return self._generate_markdown_context(projects, include_locked)
    
    def _retrieve_knowledge(self, projects: List[Project], max_results: int, config_path: Optional[str] = None) -> tuple[str, List[Dict[str, Any]]]:
        """从知识库检索相关内容"""
        if not projects:
            return "", []
        
        # 使用第一个项目的信息进行检索
        project = projects[0]
        
        # 构建依赖字典
        dependencies = {}
        for dep in project.dependencies:
            if dep.type in ['production', 'runtime']:
                dependencies[dep.name] = dep.version
        
        # 初始化知识库
        kb = KnowledgeBase(config_path)
        kb.initialize()
        
        # 检索
        response = kb.retrieve(
            language=project.language,
            framework=project.framework,
            dependencies=dependencies,
            max_results=max_results
        )
        
        # 整理结果
        results = []
        for result in response.results:
            results.append({
                'title': result.item.title,
                'source': result.item.source,
                'source_type': result.item.source_type,
                'relevance': result.relevance,
                'match_reasons': result.match_reasons,
                'path': result.item.path
            })
        
        return response.knowledge_context, results
    
    def _generate_markdown_context(self, projects: List[Project], include_locked: bool) -> str:
        """生成 Markdown 格式上下文"""
        lines = []
        
        lines.append("# 🛠️ Project Context Patch")
        lines.append(f"\n*Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        lines.append("## ⚠️ CRITICAL: Environment Version Alignment")
        lines.append("""
> This context patch is generated to help AI assistants understand the current 
> project environment. When generating code, ALWAYS respect the versions specified below.
> Version mismatches are a primary cause of generation quality degradation.
""")
        
        lines.append("---\n")
        
        for project in projects:
            lines.append(f"\n## 📦 Project: `{project.name}`")
            lines.append(f"- **Path**: `{project.path}`")
            lines.append(f"- **Language**: {project.language}")
            lines.append(f"- **Framework**: {project.framework}")
            
            # 运行时版本
            runtime_info = []
            if project.node_version:
                runtime_info.append(f"Node.js `{project.node_version}`")
            if project.python_version:
                runtime_info.append(f"Python `{project.python_version}`")
            if project.java_version:
                runtime_info.append(f"Java `{project.java_version}`")
            
            if runtime_info:
                lines.append("\n### 🔧 Runtime Versions")
                for r in runtime_info:
                    lines.append(f"- **{r.split()[0]}**: {r.split()[1]}")
            
            # 依赖版本
            if project.dependencies:
                lines.append("\n### 📚 Dependencies")
                
                # 按 source 分组
                by_source = {}
                for dep in project.dependencies:
                    if dep.source not in by_source:
                        by_source[dep.source] = {'production': [], 'development': [], 'locked': []}
                    
                    if dep.type == 'production' or dep.type == 'runtime':
                        by_source[dep.source]['production'].append(dep)
                    elif dep.type == 'development':
                        by_source[dep.source]['development'].append(dep)
                    elif dep.type == 'locked':
                        by_source[dep.source]['locked'].append(dep)
                
                for source, groups in by_source.items():
                    lines.append(f"\n#### From `{source}`")
                    
                    # Production
                    prod_deps = groups['production']
                    if prod_deps:
                        lines.append("\n**Production Dependencies:**")
                        for dep in prod_deps[:15]:
                            lines.append(f"- `{dep.name}`: `{dep.version}`")
                        if len(prod_deps) > 15:
                            lines.append(f"- ... and {len(prod_deps) - 15} more")
                    
                    # Locked (only if requested)
                    locked_deps = groups['locked']
                    if include_locked and locked_deps:
                        lines.append("\n**Locked Versions (Exact):**")
                        for dep in locked_deps[:10]:
                            lines.append(f"- `{dep.name}`: `{dep.version}`")
            
            lines.append("\n---\n")
        
        # 使用指南
        lines.append("""
## 💡 Usage Guidelines for AI Assistant

When working with this project, you MUST:

1. **Verify versions before suggesting code**: Check if the suggested packages/versions exist in this context
2. **Respect version constraints**: Don't suggest upgrading major versions without explicit approval
3. **Check API compatibility**: Different versions may have different APIs - always reference the versions listed above
4. **Use locked versions when available**: Prefer the exact versions from lock files for reproducibility

### Effective Context Formula:
```
Effective Context = (Current Env Versions) + (API Contracts) + (Domain-Specific Good Cases) - (Redundant Implementation Details)
```

This context patch provides the **Current Env Versions** component.
""")
        
        return '\n'.join(lines)
    
    def _generate_compact_context(self, projects: List[Project]) -> str:
        """生成紧凑格式上下文"""
        lines = []
        
        lines.append("## Current Environment Context")
        lines.append("")
        
        for project in projects:
            # 运行时信息
            runtime = []
            if project.node_version:
                runtime.append(f"Node {project.node_version}")
            if project.python_version:
                runtime.append(f"Python {project.python_version}")
            if project.java_version:
                runtime.append(f"Java")
            
            runtime_str = f"Runtimes: {', '.join(runtime)}" if runtime else ""
            
            # 关键依赖
            prod_deps = [d for d in project.dependencies if d.type in ['production', 'runtime']]
            key_deps = [f"{d.name}@{d.version}" for d in prod_deps[:8]]
            deps_str = f"Key deps: {', '.join(key_deps)}" if key_deps else ""
            
            lines.append(f"### {project.name} ({project.language} - {project.framework})")
            if runtime_str:
                lines.append(runtime_str)
            if deps_str:
                lines.append(deps_str)
            lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_json_context(self, projects: List[Project]) -> str:
        """生成 JSON 格式上下文"""
        data = {
            'generated_at': datetime.now().isoformat(),
            'projects': []
        }
        
        for project in projects:
            project_data = {
                'name': project.name,
                'path': project.path,
                'language': project.language,
                'framework': project.framework,
                'runtime_versions': {},
                'dependencies': []
            }
            
            if project.node_version:
                project_data['runtime_versions']['node'] = project.node_version
            if project.python_version:
                project_data['runtime_versions']['python'] = project.python_version
            if project.java_version:
                project_data['runtime_versions']['java'] = project.java_version
            
            for dep in project.dependencies:
                project_data['dependencies'].append(asdict(dep))
            
            data['projects'].append(project_data)
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    # ==================== 系统提示词 ====================
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是 Context Patch Agent，一个专门负责提取项目环境版本的 Sub Agent。

## 你的职责
1. 扫描项目目录结构
2. 检测项目类型（JavaScript/TypeScript, Python, Java 等）
3. 提取所有依赖版本信息
4. 获取运行时版本（Node.js, Python, Java 等）
5. 从 lock 文件获取精确版本
6. 生成结构化的上下文补丁

## 输入
- project_root: 项目根目录路径（默认当前目录 "./"）
- scan_depth: 扫描深度（默认 2）
- format: 输出格式（markdown/json/compact，默认 markdown）

## 输出格式
生成符合以下公式的上下文：
```
Effective Context = (Current Env Versions) + (API Contracts) + (Domain-Specific Good Cases) - (Redundant Implementation Details)
```

你只提供 "Current Env Versions" 部分。

## 约束
- 不修改任何文件
- 只读取和分析现有文件
- 优先使用 lock 文件中的精确版本
- 跳过 node_modules, __pycache__, target, build, dist 等目录

## 响应格式
直接输出上下文补丁内容，使用 markdown 格式，不需要额外的解释。
"""
    
    # ==================== CLI 支持 ====================
    
    def run_cli(self, args=None):
        """CLI 入口"""
        import argparse
        
        parser = argparse.ArgumentParser(description='Context Patch Sub Agent')
        parser.add_argument('project_root', nargs='?', default='.', help='Project root directory')
        parser.add_argument('--format', choices=['markdown', 'json', 'compact'], default='markdown')
        parser.add_argument('--no-locked', action='store_true', help='Exclude locked versions')
        parser.add_argument('--output', '-o', help='Output file')
        
        # 知识库相关参数
        parser.add_argument('--no-knowledge', action='store_true', help='Disable knowledge base')
        parser.add_argument('--knowledge-config', help='Knowledge base config path')
        parser.add_argument('--knowledge-limit', type=int, default=3, help='Max knowledge results')
        
        parsed_args = parser.parse_args(args)
        
        response = self.execute(
            project_root=parsed_args.project_root,
            format=parsed_args.format,
            include_locked=not parsed_args.no_locked,
            enable_knowledge=not parsed_args.no_knowledge,
            knowledge_config_path=parsed_args.knowledge_config,
            knowledge_max_results=parsed_args.knowledge_limit
        )
        
        if response.success:
            output = response.context_patch
            if parsed_args.output:
                Path(parsed_args.output).write_text(output, encoding='utf-8')
                print(f"Output written to: {parsed_args.output}")
            else:
                print(output)
        else:
            print(f"Error: {response.error}")
            exit(1)


# 导出
__all__ = ['ContextPatchAgent', 'AgentRequest', 'AgentResponse', 'Dependency', 'Project']


# CLI 入口
if __name__ == '__main__':
    agent = ContextPatchAgent()
    agent.run_cli()
