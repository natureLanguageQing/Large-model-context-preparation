"""
Context Patch - 大模型长序列错误终结者
=====================================

自动化的版本上下文管理框架，解决大模型因组件版本迭代导致的不一致问题。

主要功能：
- 自动扫描项目依赖版本
- 生成符合 Effective Context 公式的上下文补丁
- 支持多种项目类型（JavaScript, Python, Java, Go, Rust）
- 作为 Sub Agent 集成到 AI 系统

使用示例：
    from context_patch import ContextPatchAgent
    
    agent = ContextPatchAgent()
    response = agent.execute(project_root="./", format="compact")
    print(response.context_patch)

Effective Context = (Current Env Versions) + (API Contracts) + (Domain-Specific Good Cases) - (Redundant Implementation Details)
"""

__version__ = "1.0.0"
__author__ = "Context Patch Team"
__license__ = "MIT"

from context_patch.agent import ContextPatchAgent, AgentResponse

__all__ = [
    "ContextPatchAgent",
    "AgentResponse",
]
