# 自定义知识库

> Context Patch 的自定义知识库功能，允许你配置自己的配套项目存储地址，生成更加精准的上下文。

## 🎯 功能概述

自定义知识库可以存储：

- **示例项目** (`projects/`) - 你自己的项目模板
- **API 文档** (`api-docs/`) - 项目特定的 API 参考
- **Good Case / Bad Case** (`cases/`) - 最佳实践和踩坑记录
- **项目配置** (`configs/`) - 项目特定的配置文件

## 🚀 快速开始

### 1. 初始化知识库

```bash
# 使用默认路径 ~/.context-patch/knowledge
python -m context_patch.knowledge init

# 或指定自定义路径
python -m context_patch.knowledge init --path /path/to/your/knowledge
```

这会创建一个示例知识库结构：

```
knowledge/
├── my-projects/          # 示例项目
│   └── vue3-admin/
│       ├── context-info.json
│       └── README.md
├── api-references/       # API 文档
├── cases/               # Good/Bad Case
│   ├── good-vue3-store.md
│   └── bad-vue3-store.md
└── configs/              # 项目配置
```

### 2. 添加你的知识

#### 示例项目格式

在 `my-projects/` 下创建文件夹，每个项目需要包含 `context-info.json`：

```json
{
  "name": "my-vue3-project",
  "description": "我的 Vue3 项目模板",
  "language": "javascript",
  "framework": "vue",
  "tags": ["vue3", "admin", "typescript"],
  "dependencies": {
    "vue": "^3.5.0",
    "element-plus": "^2.8.0"
  }
}
```

可选添加 `README.md` 描述项目细节。

#### Case 格式

在 `cases/` 下创建 Markdown 文件：
- `good-xxx.md` - 好案例
- `bad-xxx.md` - 坏案例

```markdown
# Good Case: 标题

## 问题
描述问题...

## 解决方案
```javascript
// 代码示例
```

## 优点
1. xxx
```

### 3. 在代码中使用

```python
from context_patch.agent import ContextPatchAgent

agent = ContextPatchAgent()

response = agent.execute(
    project_root="./my-project",
    format="markdown",
    enable_knowledge=True,      # 启用知识库
    knowledge_max_results=3,   # 返回结果数
    knowledge_config_path=None # 可选：自定义配置路径
)

print(response.context_patch)        # 完整上下文（包含知识库）
print(response.knowledge_context)   # 仅知识库部分
print(response.knowledge_results)    # 知识库检索结果详情
```

### 4. CLI 使用

```bash
# 基本用法（自动启用知识库）
python -m context_patch .

# 禁用知识库
python -m context_patch . --no-knowledge

# 自定义知识库参数
python -m context_patch . --knowledge-limit 5

# 指定知识库配置
python -m context_patch . --knowledge-config /path/to/config.json
```

## 📁 目录结构说明

### context-info.json 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 项目名称 |
| description | string | 否 | 项目描述 |
| language | string | 是 | 编程语言 (javascript, python, java, go, rust) |
| framework | string | 否 | 框架 (vue, react, flask, django, spring) |
| tags | array | 否 | 自定义标签 |
| dependencies | object | 否 | 主要依赖及版本 |

### 知识源类型

| 类型 | 说明 | 扫描方式 |
|------|------|----------|
| projects | 示例项目 | 扫描包含 context-info.json 的目录 |
| api-docs | API 文档 | 扫描所有文件 |
| cases | Good/Bad Case | 扫描 .md 文件 |
| configs | 配置文件 | 扫描所有文件 |

## 🔧 管理命令

```bash
# 查看配置
python -m context_patch.knowledge config list

# 添加知识源
python -m context_patch.knowledge config add \
  --name my-projects \
  --path ~/my-knowledge/projects \
  --type projects \
  --description "我的项目" \
  --tags personal,template

# 移除知识源
python -m context_patch.knowledge config remove --name my-projects

# 重建索引
python -m context_patch.knowledge rebuild

# 搜索知识
python -m context_patch.knowledge search -l python -f flask
```

## 💡 最佳实践

1. **分类存储**：按语言/框架分类存放示例项目
2. **版本标注**：在 context-info.json 中明确标注依赖版本
3. **案例积累**：遇到问题/解决方案时及时记录到 cases
4. **定期更新**：添加新项目后运行 `rebuild` 更新索引

## 📝 配置文件

配置文件位于 `~/.context-patch/knowledge-base.json`：

```json
{
  "root": "~/.context-patch/knowledge",
  "cache_path": "~/.context-patch/knowledge/.cache/index.json",
  "auto_scan": true,
  "max_results": 5,
  "sources": [
    {
      "name": "my-projects",
      "path": "~/.context-patch/knowledge/my-projects",
      "type": "projects",
      "description": "我的示例项目",
      "tags": ["personal"],
      "enabled": true
    }
  ]
}
```
