import time
from pathlib import Path
from typing import Optional
import structlog

from .database import CodeGraphDB
from .parser import ArkTSParser
from .models import ParsedFile

logger = structlog.get_logger()


class IncrementalUpdater:
    def __init__(self, db: CodeGraphDB, parser: ArkTSParser):
        self.db = db
        self.parser = parser
        logger.info("incremental_updater_initialized")

    async def update_file(self, file_path: str) -> dict:
        start_time = time.time()
        result = {
            "file_path": file_path,
            "status": "pending",
            "duration": 0,
            "error": None
        }

        try:
            if not Path(file_path).exists():
                logger.warning("file_not_found_failed", file_path=file_path)
                result["status"] = "failed"
                result["error"] = "File not found"
                return result

            current_hash = self.db.compute_file_hash(file_path)
            old_hash = self.db.get_file_hash(file_path)

            if current_hash == old_hash:
                logger.debug("file_unchanged_skipping", file_path=file_path)
                result["status"] = "skipped"
                result["error"] = "Hash unchanged"
                return result

            logger.info("updating_file", file_path=file_path, old_hash=old_hash, new_hash=current_hash)

            file_id = self.db.get_file_id(file_path)

            if file_id is None:
                logger.info("new_file_inserting", file_path=file_path)
                modified = int(Path(file_path).stat().st_mtime)
                file_id = self.db.insert_file(file_path, current_hash, modified)
            else:
                self.db.delete_file_data(file_id)
                modified = int(Path(file_path).stat().st_mtime)
                self.db.update_file_hash(file_id, current_hash, modified)

            if hasattr(self.parser, 'parse_file_async'):
                parsed = await self.parser.parse_file_async(file_path)
            else:
                parsed = self.parser.parse_file(file_path)

            if not parsed.functions and not parsed.classes and not parsed.interfaces:
                logger.warning("no_symbols_found", file_path=file_path)

            self.db.insert_parsed_data(file_id, parsed)

            result["status"] = "success"
            result["parsed"] = {
                "functions": len(parsed.functions),
                "classes": len(parsed.classes),
                "interfaces": len(parsed.interfaces),
                "properties": len(parsed.properties),
                "imports": len(parsed.imports),
                "calls": len(parsed.calls)
            }

            logger.info(
                "file_updated_successfully",
                file_path=file_path,
                duration=time.time() - start_time,
                **result["parsed"]
            )

        except Exception as e:
            logger.error("file_update_failed", file_path=file_path, error=str(e))
            result["status"] = "error"
            result["error"] = str(e)

        finally:
            result["duration"] = time.time() - start_time

        return result

    def update_file_sync(self, file_path: str) -> dict:
        import asyncio
        return asyncio.run(self.update_file(file_path))

    async def batch_update(self, file_paths: list[str]) -> dict:
        start_time = time.time()
        results = {
            "total": len(file_paths),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        for file_path in file_paths:
            result = await self.update_file(file_path)
            if result["status"] == "success":
                results["success"] += 1
            elif result["status"] == "skipped":
                results["skipped"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "file": file_path,
                    "error": result["error"]
                })

        results["duration"] = time.time() - start_time
        logger.info("batch_update_completed", **results)
        return results
