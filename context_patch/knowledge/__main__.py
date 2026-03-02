"""
Knowledge Base CLI
==================
知识库命令行工具
"""

import sys
import argparse
import os
from pathlib import Path


def cmd_init(args):
    """初始化知识库"""
    from context_patch.knowledge import KnowledgeBase
    
    target_path = args.path or "~/.context-patch/knowledge"
    
    # 创建示例知识库
    KnowledgeBase.create_example(target_path)
    
    # 使用指定路径作为知识库根目录
    config_path = os.path.join(os.path.expanduser(target_path), "knowledge-base.json")
    
    # 初始化 - 使用创建的配置
    kb = KnowledgeBase(config_path=config_path)
    kb.initialize(force_rebuild=True)
    
    print(f"\n✅ Knowledge base initialized at: {target_path}")


def cmd_rebuild(args):
    """重建索引"""
    from context_patch.knowledge import KnowledgeBase
    
    kb = KnowledgeBase()
    kb.initialize(force_rebuild=True)
    
    print(f"\n✅ Index rebuilt with {len(kb.indexer.index.items)} items")


def cmd_search(args):
    """检索知识"""
    from context_patch.knowledge import KnowledgeBase
    
    kb = KnowledgeBase()
    
    # 解析依赖
    dependencies = {}
    if args.dependencies:
        for dep in args.dependencies:
            if '=' in dep:
                name, version = dep.split('=', 1)
                dependencies[name] = version
    
    # 解析标签
    tags = args.tags or []
    
    response = kb.retrieve(
        language=args.language,
        framework=args.framework,
        dependencies=dependencies,
        tags=tags,
        max_results=args.limit
    )
    
    if response.success:
        print(response.knowledge_context)
    else:
        print(f"Error: {response.error}")
        sys.exit(1)


def cmd_config(args):
    """管理配置"""
    from context_patch.knowledge import KnowledgeBaseConfigManager
    
    manager = KnowledgeBaseConfigManager()
    
    if args.action == "list":
        print("Knowledge Sources:")
        for source in manager.config.sources:
            status = "✓" if source.enabled else "✗"
            print(f"  {status} {source.name} ({source.type}) - {source.path}")
    
    elif args.action == "add":
        manager.add_source(
            name=args.name,
            path=args.path,
            type=args.type,
            description=args.description or "",
            tags=args.tags or []
        )
        print(f"✅ Added knowledge source: {args.name}")
    
    elif args.action == "remove":
        manager.remove_source(args.name)
        print(f"✅ Removed knowledge source: {args.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Context Patch Knowledge Base CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # init 命令
    init_parser = subparsers.add_parser("init", help="Initialize knowledge base")
    init_parser.add_argument(
        "--path", "-p",
        help="Knowledge base root path (default: ~/.context-patch/knowledge)"
    )
    init_parser.set_defaults(func=cmd_init)
    
    # rebuild 命令
    rebuild_parser = subparsers.add_parser("rebuild", help="Rebuild knowledge index")
    rebuild_parser.set_defaults(func=cmd_rebuild)
    
    # search 命令
    search_parser = subparsers.add_parser("search", help="Search knowledge")
    search_parser.add_argument("--language", "-l", help="Project language")
    search_parser.add_argument("--framework", "-f", help="Project framework")
    search_parser.add_argument("--dependencies", "-d", nargs="+", help="Dependencies (name=version)")
    search_parser.add_argument("--tags", "-t", nargs="+", help="Tags to match")
    search_parser.add_argument("--limit", type=int, default=5, help="Max results")
    search_parser.set_defaults(func=cmd_search)
    
    # config 命令
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("action", choices=["list", "add", "remove"], help="Action")
    config_parser.add_argument("--name", help="Source name")
    config_parser.add_argument("--path", help="Source path")
    config_parser.add_argument("--type", choices=["projects", "api-docs", "cases", "configs"], help="Source type")
    config_parser.add_argument("--description", help="Source description")
    config_parser.add_argument("--tags", nargs="+", help="Source tags")
    config_parser.set_defaults(func=cmd_config)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
