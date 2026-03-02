"""
Entry point for running context_patch as a module.
Usage: python -m context_patch .
"""

from context_patch.agent import ContextPatchAgent

if __name__ == '__main__':
    agent = ContextPatchAgent()
    agent.run_cli()
