"""
Knowledge Base Retriever
=======================
知识检索模块

根据当前项目环境从知识库中检索相关内容
"""

import os
import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from .base import KnowledgeIndex, KnowledgeItem, KnowledgeIndexer
from .config import KnowledgeBaseConfig, KnowledgeSource


@dataclass
class RetrievalResult:
    """检索结果"""
    item: KnowledgeItem
    score: float
    relevance: str  # 'high', 'medium', 'low'
    match_reasons: List[str] = field(default_factory=list)


@dataclass
class RetrievalRequest:
    """检索请求"""
    project_name: str
    language: Optional[str] = None
    framework: Optional[str] = None
    dependencies: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    source_types: List[str] = field(default_factory=lambda: ['project', 'case', 'api-doc', 'config'])
    max_results: int = 5


@dataclass
class RetrievalResponse:
    """检索响应"""
    success: bool
    results: List[RetrievalResult] = field(default_factory=list)
    knowledge_context: str = ""
    error: Optional[str] = None


class KnowledgeRetriever:
    """知识检索器"""
    
    def __init__(self, index: KnowledgeIndex, config: KnowledgeBaseConfig):
        self.index = index
        self.config = config
    
    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        """执行检索"""
        try:
            # 1. 筛选候选项
            candidates = self._filter_candidates(request)
            
            if not candidates:
                return RetrievalResponse(
                    success=True,
                    results=[],
                    knowledge_context="No matching knowledge found."
                )
            
            # 2. 计算相关性分数
            scored = []
            for item in candidates:
                score, reasons = self._calculate_relevance(item, request)
                if score > 0:
                    scored.append(RetrievalResult(
                        item=item,
                        score=score,
                        relevance=self._get_relevance_level(score),
                        match_reasons=reasons
                    ))
            
            # 3. 排序并返回 top K
            scored.sort(key=lambda x: x.score, reverse=True)
            results = scored[:request.max_results]
            
            # 4. 生成上下文
            context = self._generate_context(results)
            
            return RetrievalResponse(
                success=True,
                results=results,
                knowledge_context=context
            )
            
        except Exception as e:
            return RetrievalResponse(
                success=False,
                error=f"Retrieval failed: {str(e)}"
            )
    
    def _filter_candidates(self, request: RetrievalRequest) -> List[KnowledgeItem]:
        """筛选候选项"""
        candidates = []
        
        for item in self.index.items:
            # 过滤类型
            if item.source_type not in request.source_types:
                continue
            
            candidates.append(item)
        
        return candidates
    
    def _calculate_relevance(self, item: KnowledgeItem, request: RetrievalRequest) -> tuple[float, List[str]]:
        """计算相关性分数"""
        score = 0.0
        reasons = []
        
        # 语言匹配 (权重: 40)
        if request.language and item.language:
            if request.language.lower() == item.language.lower():
                score += 40
                reasons.append(f"语言匹配: {item.language}")
            elif request.language.lower() in item.language.lower() or item.language.lower() in request.language.lower():
                score += 20
                reasons.append(f"语言部分匹配: {item.language}")
        
        # 框架匹配 (权重: 30)
        if request.framework and item.framework:
            req_framework = request.framework.lower()
            item_framework = item.framework.lower()
            
            if req_framework == item_framework:
                score += 30
                reasons.append(f"框架匹配: {item.framework}")
            elif req_framework in item_framework or item_framework in req_framework:
                score += 15
                reasons.append(f"框架部分匹配: {item.framework}")
        
        # 依赖匹配 (权重: 20)
        if request.dependencies and item.dependencies:
            matched_deps = set(request.dependencies.keys()) & set(item.dependencies.keys())
            if matched_deps:
                dep_score = len(matched_deps) * 10
                score += min(dep_score, 20)  # 最多 20 分
                reasons.append(f"依赖匹配: {', '.join(matched_deps)}")
        
        # 标签匹配 (权重: 10)
        if request.tags:
            matched_tags = set(request.tags) & set(item.tags)
            if matched_tags:
                tag_score = len(matched_tags) * 5
                score += min(tag_score, 10)  # 最多 10 分
                reasons.append(f"标签匹配: {', '.join(matched_tags)}")
        
        return score, reasons
    
    def _get_relevance_level(self, score: float) -> str:
        """获取相关性等级"""
        if score >= 50:
            return 'high'
        elif score >= 20:
            return 'medium'
        else:
            return 'low'
    
    def _generate_context(self, results: List[RetrievalResult]) -> str:
        """生成知识上下文"""
        if not results:
            return ""
        
        lines = []
        lines.append("\n---\n")
        lines.append("## 📚 Related Knowledge")
        lines.append("*From your custom knowledge base*\n")
        
        for i, result in enumerate(results, 1):
            item = result.item
            lines.append(f"### {i}. {item.title}")
            lines.append(f"**Source**: {item.source} | **Type**: {item.source_type} | **Relevance**: {result.relevance}")
            
            if item.language or item.framework:
                info = []
                if item.language:
                    info.append(f"Language: {item.language}")
                if item.framework:
                    info.append(f"Framework: {item.framework}")
                lines.append(f"*{', '.join(info)}*")
            
            if result.match_reasons:
                lines.append(f"*Match reasons: {', '.join(result.match_reasons)}*")
            
            lines.append("")
            
            # 内容摘要
            content = item.content
            if len(content) > 800:
                content = content[:800] + "..."
            lines.append(content)
            lines.append("")
        
        lines.append("---\n")
        
        return '\n'.join(lines)


class KnowledgeBase:
    """
    知识库主类
    
    整合配置、索引和检索功能
    """
    
    def __init__(self, config_path: Optional[str] = None):
        from .config import KnowledgeBaseConfigManager
        
        # 加载配置
        self.config_manager = KnowledgeBaseConfigManager(config_path)
        self.config = self.config_manager.config
        
        # 初始化索引器
        self.indexer = KnowledgeIndexer(self.config.cache_path)
        
        # 初始化检索器
        self.retriever = KnowledgeRetriever(self.indexer.index, self.config)
    
    def initialize(self, force_rebuild: bool = False):
        """初始化知识库"""
        sources = [
            {
                'name': s.name,
                'path': s.path,
                'type': s.type
            }
            for s in self.config_manager.get_enabled_sources()
        ]
        
        if force_rebuild or not self.indexer.index.items:
            print("Building knowledge base index...")
            try:
                self.indexer.rebuild(sources)
                print(f"Index built with {len(self.indexer.index.items)} items")
            except PermissionError:
                # 如果没有权限写入默认缓存目录，使用临时目录
                import tempfile
                temp_cache = os.path.join(tempfile.gettempdir(), 'context-patch-index')
                print(f"Using temp cache: {temp_cache}")
                self.indexer = KnowledgeIndexer(temp_cache)
                self.indexer.rebuild(sources)
                print(f"Index built with {len(self.indexer.index.items)} items")
        else:
            print(f"Using cached index with {len(self.indexer.index.items)} items")
    
    def retrieve(self, 
                 language: Optional[str] = None,
                 framework: Optional[str] = None,
                 dependencies: Optional[Dict[str, str]] = None,
                 tags: Optional[List[str]] = None,
                 max_results: Optional[int] = None) -> RetrievalResponse:
        """检索知识"""
        # 确保索引已加载
        if not self.indexer.index.items:
            self.initialize()
        
        request = RetrievalRequest(
            project_name="",
            language=language,
            framework=framework,
            dependencies=dependencies or {},
            tags=tags or [],
            max_results=max_results or self.config.max_results
        )
        
        return self.retriever.retrieve(request)
    
    def get_knowledge_context(self,
                              language: Optional[str] = None,
                              framework: Optional[str] = None,
                              dependencies: Optional[Dict[str, str]] = None,
                              tags: Optional[List[str]] = None,
                              max_results: Optional[int] = None) -> str:
        """获取知识上下文（便捷方法）"""
        response = self.retrieve(
            language=language,
            framework=framework,
            dependencies=dependencies,
            tags=tags,
            max_results=max_results
        )
        return response.knowledge_context
    
    @staticmethod
    def create_example(target_path: str = "~/.context-patch/knowledge"):
        """创建示例知识库"""
        from .config import KnowledgeBaseConfigManager
        
        # 创建配置
        config_manager = KnowledgeBaseConfigManager()
        config = KnowledgeBaseConfigManager.create_example_config(target_path)
        
        # 保存配置到目标目录
        config_manager.config = config
        config_save_path = os.path.join(os.path.expanduser(target_path), "knowledge-base.json")
        os.makedirs(os.path.expanduser(target_path), exist_ok=True)
        
        # 临时修改配置路径进行保存
        original_cache_path = config.cache_path
        config.cache_path = os.path.join(os.path.expanduser(target_path), ".cache/index.json")
        
        # 保存配置
        manager = KnowledgeBaseConfigManager(config_save_path)
        manager.config = config
        manager.save()
        
        # 恢复原配置路径
        config.cache_path = original_cache_path
        
        # 展开基础路径用于后续使用
        base = os.path.expanduser(target_path)
        
        # 示例项目 1: Vue 3 + Element Plus
        project1_path = os.path.join(base, "my-projects/vue3-admin")
        os.makedirs(project1_path, exist_ok=True)
        
        with open(os.path.join(project1_path, "context-info.json"), 'w') as f:
            json.dump({
                "name": "vue3-admin",
                "description": "Vue 3 管理后台示例",
                "language": "javascript",
                "framework": "vue",
                "tags": ["vue3", "admin", "element-plus"],
                "dependencies": {
                    "vue": "^3.5.0",
                    "element-plus": "^2.8.0",
                    "pinia": "^2.3.0"
                }
            }, f, indent=2)
        
        with open(os.path.join(project1_path, "README.md"), 'w') as f:
            f.write("""# Vue 3 Admin 示例

## 项目结构

```
src/
├── api/          # API 接口
├── components/   # 组件
├── views/        # 页面
└── stores/       # Pinia 状态管理
```

## 关键代码示例

### 使用 Pinia

```javascript
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: null
  }),
  actions: {
    async fetchUser() {
      const res = await fetch('/api/user')
      this.userInfo = await res.json()
    }
  }
})
```

### 使用 Element Plus 表格

```vue
<template>
  <el-table :data="tableData">
    <el-table-column prop="name" label="名称" />
    <el-table-column prop="status" label="状态">
      <template #default="{ row }">
        <el-tag :type="row.status === 1 ? 'success' : 'danger'">
          {{ row.status === 1 ? '启用' : '禁用' }}
        </el-tag>
      </template>
    </el-table-column>
  </el-table>
</template>
```
""")
        
        # 示例案例
        cases_path = os.path.join(base, "cases")
        
        with open(os.path.join(cases_path, "good-vue3-store.md"), 'w') as f:
            f.write("""# Good Case: Vue 3 Pinia 状态管理

## 问题

如何在 Vue 3 中管理复杂状态？

## 解决方案

使用 Pinia 的组合式 API 风格定义 store：

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCounterStore = defineStore('counter', () => {
  // 状态
  const count = ref(0)
  
  // 计算属性
  const doubleCount = computed(() => count.value * 2)
  
  // 方法
  function increment() {
    count.value++
  }
  
  return { count, doubleCount, increment }
})
```

## 优点

1. TypeScript 支持更好
2. 代码组织更清晰
3. 易于测试
""")
        
        with open(os.path.join(cases_path, "bad-vue3-store.md"), 'w') as f:
            f.write("""# Bad Case: Vue 2 风格的状态管理

## 问题

在 Vue 3 项目中使用 Vue 2 的 Vuex 写法

## 错误示例

```javascript
// 不要这样做！
import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    count: 0
  },
  mutations: {
    increment(state) {
      state.count++
    }
  }
})
```

## 问题

1. Vuex 4 虽然兼容，但不如 Pinia
2. 不支持组合式 API
3. 样板代码多
""")
        
        print(f"Example knowledge base created at: {base}")
        print("Run 'python -m context_patch.knowledge init' to initialize")


# 导出
__all__ = [
    'RetrievalResult',
    'RetrievalRequest', 
    'RetrievalResponse',
    'KnowledgeRetriever',
    'KnowledgeBase'
]
