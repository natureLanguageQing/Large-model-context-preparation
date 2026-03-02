# Context Patch

> 🤖 大模型长序列错误终结者 - 自动化的版本上下文管理框架

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![GitHub Stars](https://img.shields.io/github/stars/yourusername/context-patch?style=social)](https://github.com/yourusername/context-patch/stargazers)

## 🎯 核心问题

**为什么长序列中大模型依旧会犯错误？**

这是我们在生产环境中反复遇到的问题。经过深入分析，我们发现了根本原因：

### 1. 组件版本迭代带来的不一致

大模型在预训练阶段虽然使用了蒙特卡洛随机接入进行长流程选择最优，但**放弃了对代码底层组件迭代所带来的不一致问题的处理**。

这导致大模型时常出现：
- ❌ 版本接口参数不匹配
- ❌ 建议使用已弃用的 API
- ❌ 生成与当前环境不兼容的代码

### 2. 最短最优路径的生成惯性

大模型倾向于选择"最短最优路径"，这意味着：
- 使用最常见的解决方案
- 忽略项目特定的版本约束
- 产生与新技术组件不匹配的"惯性代码"

### 3. 上下文膨胀导致的质量衰减

当上下文过长时，关键信息被稀释，模型更容易犯错。

---

## 💡 核心架构思想

### Effective Context 公式

我们提出了一套完整的上下文优化公式：

```
Effective Context = (Current Env Versions) + (API Contracts) + (Domain-Specific Good Cases) - (Redundant Implementation Details)
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Effective Context                            │
├─────────────────────────────────────────────────────────────────────┤
│  Current Env Versions    │  API Contracts      │  Good Cases      │
│  ────────────────────    │  ───────────────    │  ──────────      │
│  • 运行时版本              │  • 接口定义          │  • Good Case    │
│  • 依赖版本                │  • 参数规范          │  • Bad Case      │
│  • 框架版本                │  • 返回值格式        │  • 最佳实践       │
├─────────────────────────────────────────────────────────────────────┤
│                        - Redundant Details                          │
│                        （冗余实现细节）                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Skill + Sub Agent 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Main Agent                                │
│                    (你的主 AI 助手)                              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────┴────────────┐
          │                        │
          ▼                        ▼
┌─────────────────┐      ┌─────────────────────┐
│ Context Patch   │      │ Skills Sub Agent    │
│ Sub Agent       │      │ (任务聚焦)           │
│                 │      │                     │
│ • 版本提取       │      │ • 任务拆解           │
│ • 环境检测       │      │ • 上下文隔离         │
│ • 上下文生成     │      │ • 质量优化           │
└─────────────────┘      └─────────────────────┘
```

**核心理念**：
1. **Skills** - 通过固定流程优化上下文长度，聚焦任务
2. **Sub Agent** - 拆解任务，让每个子任务获得独立的上下文理解
3. **从两个维度优化** - 长度 + 上下文质量

### 版本对齐的工作流程

```
1. Task Start
       │
       ▼
2. 调用 Context Patch Agent
       │
       ├── 扫描项目目录
       ├── 检测项目类型
       ├── 提取依赖版本
       ├── 获取运行时版本
       └── 生成上下文补丁
       │
       ▼
3. 注入上下文到 Main Agent
       │
       ▼
4. Main Agent 基于精确版本生成代码
       │
       ▼
5. ✅ 版本匹配，质量保证
```

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/yourusername/context-patch.git
cd context-patch
pip install -r requirements.txt
```

### 基本用法

```python
from context_patch.agent import ContextPatchAgent

agent = ContextPatchAgent()

# 执行 Agent
response = agent.execute(
    project_root="/path/to/your/project",
    format="compact"  # markdown, json, compact
)

print(response.context_patch)
```

### CLI 用法

```bash
# 生成紧凑格式（适合嵌入提示词）
python -m context_patch . --format compact

# 生成完整 Markdown
python -m context_patch . --format markdown

# 输出到文件
python -m context_patch . -o context-patch.md
```

**输出示例**：

```markdown
## Current Environment Context

### frontend (JavaScript - Vue 3.5.13)
Runtimes: Node v22.19.0
Key deps: vue@^3.5.13, element-plus@^2.8.8, pinia@^2.3.0

### backend-python (Python - Flask)
Runtimes: Python v3.9.6
Key deps: Flask@==3.0.0, langchain@>=0.3.0, chromadb@>=0.4.0
```

---

## 🏗️ 项目架构

```
context-patch/
├── context_patch/           # 核心包
│   ├── __init__.py
│   ├── agent.py            # Context Patch Agent 实现
│   ├── extractors/         # 依赖提取器
│   │   ├── __init__.py
│   │   ├── npm.py          # npm/package.json 提取器
│   │   ├── pip.py          # pip/requirements.txt 提取器
│   │   ├── maven.py        # Maven/pom.xml 提取器
│   │   └── lock.py         # Lock 文件提取器
│   ├── generators/         # 上下文生成器
│   │   ├── __init__.py
│   │   ├── markdown.py
│   │   ├── json.py
│   │   └── compact.py
│   └── config.py           # 配置
├── skill/                  # Skill 定义
│   └── skill.yaml
├── tests/                 # 测试
├── docs/                  # 文档
├── README.md
├── LICENSE
└── requirements.txt
```

---

## 🔧 支持的项目类型

| 语言 | 框架 | 依赖文件 | Lock 文件 |
|------|------|----------|-----------|
| JavaScript/TypeScript | Vue, React, Next.js | `package.json` | `yarn.lock`, `package-lock.json` |
| Python | Flask, Django, FastAPI | `requirements.txt` | `Pipfile.lock`, `poetry.lock` |
| Java | Spring Boot | `pom.xml` | - |
| Go | - | `go.mod` | - |
| Rust | - | `Cargo.toml` | - |

---

## 🤝 集成示例

### 集成到 Cursor

创建 `.cursorrules`：

```markdown
# Context Patch Rule

每次任务开始时，先调用 context-patch-agent 获取版本信息：

```
{{context-patch-agent: project_root="./", format="compact"}}
```

禁止建议未在 context-patch 中列出的包版本。
```

### 集成到 LangChain

```python
from langchain.agents import AgentExecutor, create_openai_functions_agent
from context_patch.agent import ContextPatchAgent

# 创建 Context Patch Tool
def get_context_patch(project_root: str) -> str:
    agent = ContextPatchAgent()
    response = agent.execute(project_root=project_root, format="compact")
    return response.context_patch

# 注册为 Tool
tools = [
    Tool(
        name="context-patch",
        func=get_context_patch,
        description="获取项目版本上下文信息"
    )
]

# 使用 Agent
agent = create_openai_functions_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
```

---

## 📚 深入阅读

- [架构设计文档](./docs/ARCHITECTURE.md)
- [API 参考](./docs/API.md)
- [案例研究](./docs/CASES.md)

---

## 🧪 运行测试

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest tests/ -v

# 运行示例
python examples/basic_usage.py
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

---

## 📄 License

MIT License - 查看 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

感谢以下开源项目：

- [Python](https://www.python.org/)
- 所有依赖的贡献者

---

**核心理念**: 通过自动化的版本上下文管理，让大模型始终在"正确的上下文中"工作，从根本上解决长序列错误问题。

```
与其让大模型"猜"版本，不如告诉它"确切"的版本。
```
