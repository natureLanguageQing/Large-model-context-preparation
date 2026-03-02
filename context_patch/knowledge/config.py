"""
Knowledge Base Configuration
============================
自定义知识库配置模块

允许用户配置多个知识库路径，每个知识库可以包含：
- 示例项目 (projects/)
- API 文档 (api-docs/)
- Good Case / Bad Case (cases/)
- 项目特定的配置文件 (configs/)
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class KnowledgeSource:
    """知识源配置"""
    name: str
    path: str
    type: str  # 'projects', 'api-docs', 'cases', 'configs'
    description: str = ""
    tags: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class KnowledgeBaseConfig:
    """知识库配置"""
    # 知识库根目录
    root: str = "~/.context-patch/knowledge"
    
    # 启用的知识源列表
    sources: List[KnowledgeSource] = field(default_factory=list)
    
    # 知识库索引缓存路径
    cache_path: str = "~/.context-patch/knowledge/.cache"
    
    # 是否自动扫描
    auto_scan: bool = True
    
    # 检索时返回的最大结果数
    max_results: int = 5
    
    # 知识库元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeBaseConfigManager:
    """知识库配置管理器"""
    
    DEFAULT_CONFIG_NAME = "knowledge-base.json"
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = self.load()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置路径"""
        return os.path.join(
            os.path.expanduser("~/.context-patch"),
            self.DEFAULT_CONFIG_NAME
        )
    
    def load(self) -> KnowledgeBaseConfig:
        """加载配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                config = KnowledgeBaseConfig(
                    root=data.get('root', '~/.context-patch/knowledge'),
                    cache_path=data.get('cache_path', '~/.context-patch/knowledge/.cache'),
                    auto_scan=data.get('auto_scan', True),
                    max_results=data.get('max_results', 5),
                    metadata=data.get('metadata', {}),
                    sources=[
                        KnowledgeSource(
                            name=s['name'],
                            path=s['path'],
                            type=s['type'],
                            description=s.get('description', ''),
                            tags=s.get('tags', []),
                            enabled=s.get('enabled', True)
                        )
                        for s in data.get('sources', [])
                    ]
                )
                return config
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")
        
        # 返回默认配置
        return self._create_default_config()
    
    def _create_default_config(self) -> KnowledgeBaseConfig:
        """创建默认配置"""
        return KnowledgeBaseConfig(
            root="~/.context-patch/knowledge",
            sources=[
                KnowledgeSource(
                    name="default-examples",
                    path="~/.context-patch/knowledge/examples",
                    type="projects",
                    description="官方示例项目",
                    tags=["examples", "official"]
                ),
                KnowledgeSource(
                    name="default-cases",
                    path="~/.context-patch/knowledge/cases",
                    type="cases",
                    description="Good Case / Bad Case 案例库",
                    tags=["cases", "best-practices"]
                ),
            ],
            cache_path="~/.context-patch/knowledge/.cache",
            auto_scan=True,
            max_results=5
        )
    
    def save(self):
        """保存配置"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        data = {
            'root': self.config.root,
            'cache_path': self.config.cache_path,
            'auto_scan': self.config.auto_scan,
            'max_results': self.config.max_results,
            'metadata': self.config.metadata,
            'sources': [
                {
                    'name': s.name,
                    'path': s.path,
                    'type': s.type,
                    'description': s.description,
                    'tags': s.tags,
                    'enabled': s.enabled
                }
                for s in self.config.sources
            ]
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_source(self, name: str, path: str, type: str, 
                   description: str = "", tags: List[str] = None):
        """添加知识源"""
        source = KnowledgeSource(
            name=name,
            path=path,
            type=type,
            description=description,
            tags=tags or []
        )
        self.config.sources.append(source)
        self.save()
    
    def remove_source(self, name: str):
        """移除知识源"""
        self.config.sources = [s for s in self.config.sources if s.name != name]
        self.save()
    
    def get_enabled_sources(self) -> List[KnowledgeSource]:
        """获取启用的知识源"""
        return [s for s in self.config.sources if s.enabled]
    
    def get_sources_by_type(self, type: str) -> List[KnowledgeSource]:
        """根据类型获取知识源"""
        return [s for s in self.config.sources if s.type == type and s.enabled]
    
    @staticmethod
    def create_example_config(target_path: str = "~/.context-patch/knowledge"):
        """创建示例配置"""
        config = KnowledgeBaseConfig()
        config.root = target_path
        
        # 添加示例知识源
        base = os.path.expanduser(target_path)
        
        config.sources = [
            KnowledgeSource(
                name="my-projects",
                path=os.path.join(base, "my-projects"),
                type="projects",
                description="我自己的示例项目",
                tags=["personal", "projects"]
            ),
            KnowledgeSource(
                name="api-references",
                path=os.path.join(base, "api-references"),
                type="api-docs",
                description="API 参考文档",
                tags=["api", "docs"]
            ),
            KnowledgeSource(
                name="best-practices",
                path=os.path.join(base, "cases"),
                type="cases",
                description="最佳实践案例",
                tags=["cases", "best-practices"]
            ),
            KnowledgeSource(
                name="project-configs",
                path=os.path.join(base, "configs"),
                type="configs",
                description="项目特定配置",
                tags=["configs", "settings"]
            ),
        ]
        
        # 创建目录结构
        for source in config.sources:
            os.makedirs(os.path.expanduser(source.path), exist_ok=True)
        
        # 创建 README
        readme_content = """# Context Patch Knowledge Base

## 目录结构

```
knowledge/
├── my-projects/     # 你自己的示例项目
├── api-references/  # API 参考文档
├── cases/          # Good Case / Bad Case
└── configs/         # 项目特定配置
```

## 使用方法

### 1. 添加示例项目

在 `my-projects/` 目录下添加你的示例项目。

每个项目应该包含：
- 完整的项目结构
- `context-info.json` 描述项目环境

### 2. 添加 Good Case / Bad Case

在 `cases/` 目录下创建案例文件：
- `good-xxx.md` - 好的案例
- `bad-xxx.md` - 坏的案例
- 使用标签区分类型

### 3. API 参考文档

在 `api-references/` 目录下添加 API 文档。

---
更多用法请参考官方文档。
"""
        
        with open(os.path.join(base, "README.md"), 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        return config


# 导出
__all__ = [
    'KnowledgeSource', 
    'KnowledgeBaseConfig', 
    'KnowledgeBaseConfigManager'
]
