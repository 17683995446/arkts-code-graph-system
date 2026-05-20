import argparse
import asyncio
import yaml
import sys
import signal
from pathlib import Path
import structlog

from .database import CodeGraphDB
from .parser import ArkTSParser
from .watcher import FileWatcher
from .incremental import IncrementalUpdater

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


def load_config(config_path: str = "config.yaml") -> dict:
    config_file = Path(config_path)
    if not config_file.exists():
        logger.warning("config_not_found_using_defaults", path=config_path)
        return {
            "siliconflow": {
                "api_key": "sk-uqelhavcdhfxjzjesdenxpbtqombamjniazzjtbssmdcwdvg",
                "model": "qwen/qwen2.5-coder-7b-instruct",
                "base_url": "https://api.siliconflow.cn/v1"
            },
            "watcher": {
                "debounce_delay": 1.0,
                "file_pattern": "**/*.ets",
                "exclude_patterns": ["**/node_modules/**", "**/.arkui/**", "**/build/**"]
            },
            "database": {
                "path": "code_graph.db"
            }
        }
    
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def cmd_scan(args, config: dict):
    logger.info("starting_full_scan", root_dir=args.root)
    
    db = CodeGraphDB(config["database"]["path"])
    parser = ArkTSParser(
        api_key=config["siliconflow"]["api_key"],
        model=config["siliconflow"]["model"],
        base_url=config["siliconflow"]["base_url"]
    )
    updater = IncrementalUpdater(db, parser)
    
    root = Path(args.root)
    files = list(root.glob(args.pattern))
    
    print(f"Found {len(files)} files matching pattern '{args.pattern}'")
    print("Scanning files and parsing with LLM...")
    
    for i, file_path in enumerate(files, 1):
        result = await updater.update_file(str(file_path))
        if result["status"] == "success":
            parsed = result.get("parsed", {})
            print(f"[{i}/{len(files)}] ✓ {file_path.name}: {parsed.get('functions', 0)} functions, {parsed.get('classes', 0)} classes")
        else:
            print(f"[{i}/{len(files)}] ✗ {file_path.name}: {result.get('error', 'Unknown error')}")
    
    await parser.close()
    db.close()
    print("\nFull scan completed!")


async def cmd_watch(args, config: dict):
    logger.info("starting_watch_mode", root_dir=args.root)
    
    db = CodeGraphDB(config["database"]["path"])
    parser = ArkTSParser(
        api_key=config["siliconflow"]["api_key"],
        model=config["siliconflow"]["model"],
        base_url=config["siliconflow"]["base_url"]
    )
    updater = IncrementalUpdater(db, parser)
    
    async def on_file_changed(file_path: str):
        result = await updater.update_file(file_path)
        if result["status"] == "success":
            parsed = result.get("parsed", {})
            print(f"\n✓ Updated {Path(file_path).name}: {parsed.get('functions', 0)} functions, {parsed.get('classes', 0)} classes (took {result['duration']:.2f}s)")
        elif result["status"] == "skipped":
            print(f"\n- Skipped {Path(file_path).name}: no changes")
        else:
            print(f"\n✗ Failed {Path(file_path).name}: {result.get('error', 'Unknown error')}")
    
    watcher = FileWatcher(
        root_dir=args.root,
        callback=lambda p: asyncio.create_task(on_file_changed(p)),
        file_pattern=args.pattern,
        exclude_patterns=config["watcher"].get("exclude_patterns", []),
        debounce_delay=config["watcher"].get("debounce_delay", 1.0)
    )
    
    def signal_handler(sig, frame):
        print("\n\nStopping watcher...")
        watcher.stop()
        asyncio.get_event_loop().run_until_complete(parser.close())
        db.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"Watching {args.root} for changes (pattern: {args.pattern})")
    print("Press Ctrl+C to stop...")
    
    watcher.start()
    
    while watcher.is_running():
        await asyncio.sleep(1)


def cmd_query(args, config: dict):
    db = CodeGraphDB(config["database"]["path"])
    
    if args.symbol:
        results = db.search_symbol(args.symbol)
        if results["functions"] or results["classes"] or results["interfaces"]:
            print(f"\nSearch results for '{args.symbol}':")
            for func in results["functions"]:
                print(f"  📦 Function: {func['name']} ({func['file_path']})")
            for cls in results["classes"]:
                print(f"  📁 Class: {cls['name']} ({cls['file_path']})")
            for iface in results["interfaces"]:
                print(f"  🔗 Interface: {iface['name']} ({iface['file_path']})")
        else:
            print(f"No results found for '{args.symbol}'")
    
    elif args.file:
        file_info = db.get_file_by_path(args.file)
        if file_info:
            print(f"\nFile: {file_info.path}")
            print(f"Hash: {file_info.hash[:16]}...")
            print(f"Modified: {file_info.modified}")
            print(f"Last parsed: {file_info.last_parsed}")
            
            file_id = db.get_file_id(args.file)
            functions = db.get_functions_in_file(file_id)
            classes = db.get_classes_in_file(file_id)
            
            if functions:
                print(f"\nFunctions ({len(functions)}):")
                for func in functions:
                    print(f"  - {func.name}({', '.join([p['name'] for p in func.params])}) -> {func.return_type}")
            
            if classes:
                print(f"\nClasses ({len(classes)}):")
                for cls in classes:
                    extends = f" extends {cls.extends}" if cls.extends else ""
                    print(f"  - {cls.name}{extends}")
        else:
            print(f"File '{args.file}' not found in database")
    
    elif args.list:
        cursor = db.conn.execute("SELECT path, last_parsed FROM files ORDER BY last_parsed DESC")
        rows = cursor.fetchall()
        if rows:
            print(f"\nTracked files ({len(rows)}):")
            for path, last_parsed in rows:
                print(f"  - {path}")
        else:
            print("No files tracked yet")
    
    db.close()


async def cmd_update(args, config: dict):
    db = CodeGraphDB(config["database"]["path"])
    parser = ArkTSParser(
        api_key=config["siliconflow"]["api_key"],
        model=config["siliconflow"]["model"],
        base_url=config["siliconflow"]["base_url"]
    )
    updater = IncrementalUpdater(db, parser)
    
    result = await updater.update_file(args.file)
    
    if result["status"] == "success":
        parsed = result.get("parsed", {})
        print(f"✓ Updated {args.file}")
        print(f"  Functions: {parsed.get('functions', 0)}")
        print(f"  Classes: {parsed.get('classes', 0)}")
        print(f"  Interfaces: {parsed.get('interfaces', 0)}")
        print(f"  Duration: {result['duration']:.2f}s")
    else:
        print(f"✗ Failed: {result.get('error', 'Unknown error')}")
    
    await parser.close()
    db.close()


def main():
    parser = argparse.ArgumentParser(
        description="动态更新版 ArkTS → SQLite 代码知识图谱系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s scan ./my-project                    # 全量扫描
  %(prog)s watch ./my-project                    # 监听模式
  %(prog)s query --symbol UserService            # 搜索符号
  %(prog)s query --file src/Index.ets            # 查询文件详情
  %(prog)s query --list                          # 列出所有文件
  %(prog)s update src/HomePage.ets               # 更新单个文件
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    scan_parser = subparsers.add_parser("scan", help="Full scan of project")
    scan_parser.add_argument("root", help="Project root directory")
    scan_parser.add_argument("--pattern", default="**/*.ets", help="File pattern to match")
    
    watch_parser = subparsers.add_parser("watch", help="Watch mode for incremental updates")
    watch_parser.add_argument("root", help="Project root directory")
    watch_parser.add_argument("--pattern", default="**/*.ets", help="File pattern to match")
    
    query_parser = subparsers.add_parser("query", help="Query the code graph")
    query_group = query_parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--symbol", help="Search for a symbol name")
    query_group.add_argument("--file", help="Get details for a specific file")
    query_group.add_argument("--list", action="store_true", help="List all tracked files")
    
    update_parser = subparsers.add_parser("update", help="Update a single file")
    update_parser.add_argument("file", help="File path to update")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    config = load_config()
    
    if args.command == "scan":
        asyncio.run(cmd_scan(args, config))
    elif args.command == "watch":
        asyncio.run(cmd_watch(args, config))
    elif args.command == "query":
        cmd_query(args, config)
    elif args.command == "update":
        asyncio.run(cmd_update(args, config))


if __name__ == "__main__":
    main()
