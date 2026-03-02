"""
Knowledge Base Module
====================
自定义知识库模块

支持功能：
- 配置多个知识源路径
- 扫描和索引知识内容
- 根据项目环境检索相关知识
- 生成知识上下文

快速开始：

```python
from context_patch.knowledge import KnowledgeBase

# 初始化知识库
kb = KnowledgeBase()
kb.initialize()

# 获取知识上下文
context = kb.get_knowledge_context(
    language="javascript",
    framework="vue",
    dependencies={"vue": "^3.5.0", "element-plus": "^2.8.0"},
    max_results=3
)

print(context)
```

CLI 用法：

```bash
# 初始化知识库
python -m context_patch.knowledge init

# 重建索引
python -m context_patch.knowledge rebuild

# 检索知识
python -m context_patch.knowledge search --language python --framework flask
```
"""

from .config import KnowledgeSource, KnowledgeBaseConfig, KnowledgeBaseConfigManager
from .base import KnowledgeItem, KnowledgeIndex, KnowledgeIndexer
from .retriever import RetrievalResult, RetrievalRequest, RetrievalResponse, KnowledgeRetriever, KnowledgeBase

__all__ = [
    # 配置
    'KnowledgeSource',
    'KnowledgeBaseConfig',
    'KnowledgeBaseConfigManager',
    # 索引
    'KnowledgeItem',
    'KnowledgeIndex',
    'KnowledgeIndexer',
    # 检索
    'RetrievalResult',
    'RetrievalRequest',
    'RetrievalResponse',
    'KnowledgeRetriever',
    # 主类
    'KnowledgeBase'
]
