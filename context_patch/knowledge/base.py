"""
Knowledge Base Indexer
======================
知识库索引模块

扫描知识库中的内容，建立索引以便快速检索
"""

import os
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class KnowledgeItem:
    """知识项"""
    id: str
    title: str
    content: str
    source: str
    source_type: str  # 'project', 'api-doc', 'case', 'config'
    path: str
    tags: List[str] = field(default_factory=list)
    language: Optional[str] = None
    framework: Optional[str] = None
    dependencies: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    modified_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.modified_at:
            self.modified_at = self.created_at


@dataclass
class KnowledgeIndex:
    """知识库索引"""
    items: List[KnowledgeItem] = field(default_factory=list)
    last_updated: str = ""
    version: str = "1.0.0"
    
    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()
    
    def add_item(self, item: KnowledgeItem):
        """添加知识项"""
        self.items.append(item)
        self.last_updated = datetime.now().isoformat()
    
    def get_by_id(self, item_id: str) -> Optional[KnowledgeItem]:
        """根据 ID 获取知识项"""
        for item in self.items:
            if item.id == item_id:
                return item
        return None
    
    def get_by_tags(self, tags: List[str]) -> List[KnowledgeItem]:
        """根据标签获取知识项"""
        result = []
        for item in self.items:
            if any(tag in item.tags for tag in tags):
                result.append(item)
        return result
    
    def get_by_language(self, language: str) -> List[KnowledgeItem]:
        """根据语言获取知识项"""
        return [item for item in self.items if item.language == language]
    
    def get_by_framework(self, framework: str) -> List[KnowledgeItem]:
        """根据框架获取知识项"""
        return [item for item in self.items if item.framework == framework]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'items': [
                {
                    'id': item.id,
                    'title': item.title,
                    'content': item.content,
                    'source': item.source,
                    'source_type': item.source_type,
                    'path': item.path,
                    'tags': item.tags,
                    'language': item.language,
                    'framework': item.framework,
                    'dependencies': item.dependencies,
                    'metadata': item.metadata,
                    'created_at': item.created_at,
                    'modified_at': item.modified_at,
                }
                for item in self.items
            ],
            'last_updated': self.last_updated,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeIndex':
        """从字典创建"""
        items = [
            KnowledgeItem(
                id=item['id'],
                title=item['title'],
                content=item['content'],
                source=item['source'],
                source_type=item['source_type'],
                path=item['path'],
                tags=item.get('tags', []),
                language=item.get('language'),
                framework=item.get('framework'),
                dependencies=item.get('dependencies', {}),
                metadata=item.get('metadata', {}),
                created_at=item.get('created_at', ''),
                modified_at=item.get('modified_at', ''),
            )
            for item in data.get('items', [])
        ]
        return cls(
            items=items,
            last_updated=data.get('last_updated', ''),
            version=data.get('version', '1.0.0')
        )


class KnowledgeIndexer:
    """知识库索引器"""
    
    def __init__(self, cache_path: Optional[str] = None):
        self.cache_path = cache_path or "~/.context-patch/knowledge/.cache/index.json"
        self.index = self._load_index()
    
    def _load_index(self) -> KnowledgeIndex:
        """加载索引"""
        path = os.path.expanduser(self.cache_path)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return KnowledgeIndex.from_dict(data)
            except Exception as e:
                print(f"Warning: Failed to load index: {e}")
        return KnowledgeIndex()
    
    def save_index(self):
        """保存索引"""
        path = os.path.expanduser(self.cache_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.index.to_dict(), f, indent=2, ensure_ascii=False)
    
    def scan_source(self, source_path: str, source_type: str, source_name: str) -> List[KnowledgeItem]:
        """扫描知识源"""
        items = []
        path = os.path.expanduser(source_path)
        
        if not os.path.exists(path):
            return items
        
        if source_type == 'projects':
            items.extend(self._scan_projects(path, source_name))
        elif source_type == 'api-docs':
            items.extend(self._scan_api_docs(path, source_name))
        elif source_type == 'cases':
            items.extend(self._scan_cases(path, source_name))
        elif source_type == 'configs':
            items.extend(self._scan_configs(path, source_name))
        
        return items
    
    def _scan_projects(self, path: str, source_name: str) -> List[KnowledgeItem]:
        """扫描示例项目"""
        items = []
        
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if not os.path.isdir(item_path):
                continue
            if item.startswith('.'):
                continue
            
            # 查找 context-info.json
            info_file = os.path.join(item_path, 'context-info.json')
            if os.path.exists(info_file):
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    
                    item_id = self._generate_id(item_path)
                    
                    # 读取 README 如果存在
                    readme = ""
                    readme_path = os.path.join(item_path, 'README.md')
                    if os.path.exists(readme_path):
                        with open(readme_path, 'r', encoding='utf-8') as f:
                            readme = f.read()
                    
                    knowledge_item = KnowledgeItem(
                        id=item_id,
                        title=info.get('name', item),
                        content=readme or info.get('description', ''),
                        source=source_name,
                        source_type='project',
                        path=item_path,
                        tags=info.get('tags', []),
                        language=info.get('language'),
                        framework=info.get('framework'),
                        dependencies=info.get('dependencies', {}),
                        metadata=info.get('metadata', {})
                    )
                    items.append(knowledge_item)
                except Exception as e:
                    print(f"Warning: Failed to scan project {item}: {e}")
        
        return items
    
    def _scan_api_docs(self, path: str, source_name: str) -> List[KnowledgeItem]:
        """扫描 API 文档"""
        items = []
        
        for root, dirs, files in os.walk(path):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    item_id = self._generate_id(file_path)
                    
                    # 根据文件扩展名确定语言
                    language = self._get_language_from_ext(file)
                    
                    knowledge_item = KnowledgeItem(
                        id=item_id,
                        title=os.path.splitext(file)[0],
                        content=content[:5000],  # 限制内容长度
                        source=source_name,
                        source_type='api-doc',
                        path=rel_path,
                        tags=[language] if language else [],
                        language=language,
                    )
                    items.append(knowledge_item)
                except Exception as e:
                    print(f"Warning: Failed to scan API doc {file}: {e}")
        
        return items
    
    def _scan_cases(self, path: str, source_name: str) -> List[KnowledgeItem]:
        """扫描案例"""
        items = []
        
        for file in os.listdir(path):
            if file.startswith('.'):
                continue
            
            file_path = os.path.join(path, file)
            if not os.path.isfile(file_path):
                continue
            
            # 只处理 markdown 文件
            if not file.endswith('.md'):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                item_id = self._generate_id(file_path)
                
                # 解析文件名获取类型
                case_type = 'unknown'
                if file.startswith('good-'):
                    case_type = 'good'
                elif file.startswith('bad-'):
                    case_type = 'bad'
                
                tags = [case_type]
                if 'vue' in file.lower():
                    tags.append('vue')
                if 'react' in file.lower():
                    tags.append('react')
                if 'python' in file.lower():
                    tags.append('python')
                
                knowledge_item = KnowledgeItem(
                    id=item_id,
                    title=os.path.splitext(file)[0],
                    content=content,
                    source=source_name,
                    source_type='case',
                    path=file,
                    tags=tags,
                    metadata={'case_type': case_type}
                )
                items.append(knowledge_item)
            except Exception as e:
                print(f"Warning: Failed to scan case {file}: {e}")
        
        return items
    
    def _scan_configs(self, path: str, source_name: str) -> List[KnowledgeItem]:
        """扫描配置文件"""
        items = []
        
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    item_id = self._generate_id(file_path)
                    
                    # 根据目录名推断标签
                    tags = [os.path.dirname(rel_path)] if os.path.dirname(rel_path) else []
                    
                    knowledge_item = KnowledgeItem(
                        id=item_id,
                        title=os.path.splitext(file)[0],
                        content=content[:3000],
                        source=source_name,
                        source_type='config',
                        path=rel_path,
                        tags=tags,
                    )
                    items.append(knowledge_item)
                except Exception as e:
                    print(f"Warning: Failed to scan config {file}: {e}")
        
        return items
    
    def _generate_id(self, path: str) -> str:
        """生成唯一 ID"""
        return hashlib.md5(path.encode()).hexdigest()[:12]
    
    def _get_language_from_ext(self, filename: str) -> Optional[str]:
        """根据文件扩展名获取语言"""
        ext_map = {
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.py': 'python',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.md': 'markdown',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }
        ext = os.path.splitext(filename)[1].lower()
        return ext_map.get(ext)
    
    def build_index(self, sources: List[Dict[str, Any]]) -> KnowledgeIndex:
        """构建完整索引"""
        self.index = KnowledgeIndex()
        
        for source in sources:
            items = self.scan_source(
                source['path'],
                source['type'],
                source['name']
            )
            for item in items:
                self.index.add_item(item)
        
        self.save_index()
        return self.index
    
    def rebuild(self, sources: List[Dict[str, Any]]):
        """重建索引"""
        self.build_index(sources)


# 导出
__all__ = ['KnowledgeItem', 'KnowledgeIndex', 'KnowledgeIndexer']
