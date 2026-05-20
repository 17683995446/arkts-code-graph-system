import sqlite3
import json
import hashlib
import time
import threading
from pathlib import Path
from typing import Optional
import structlog

from .models import FileInfo, FunctionInfo, ClassInfo, InterfaceInfo, PropertyInfo, ImportInfo, CallInfo, ParsedFile

logger = structlog.get_logger()


class CodeGraphDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.execute("PRAGMA foreign_keys = ON")
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    @property
    def conn(self):
        return self._get_conn()

    def checkpoint(self):
        conn = self._get_conn()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        
    def _init_db(self):
        conn = self._get_conn()
        self._create_tables(conn)
        logger.info("database_initialized", db_path=self.db_path)

    def _create_tables(self, conn):
        schema = """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            hash BLOB NOT NULL,
            modified INTEGER NOT NULL,
            last_parsed INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS functions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            return_type TEXT,
            params TEXT,
            modifiers TEXT,
            start_line INTEGER,
            end_line INTEGER,
            doc_comment TEXT,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            extends TEXT,
            implements TEXT,
            modifiers TEXT,
            start_line INTEGER,
            end_line INTEGER,
            doc_comment TEXT,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS interfaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            extends TEXT,
            modifiers TEXT,
            start_line INTEGER,
            end_line INTEGER,
            doc_comment TEXT,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            class_id INTEGER,
            name TEXT NOT NULL,
            type TEXT,
            modifiers TEXT,
            default_value TEXT,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            import_path TEXT NOT NULL,
            import_type TEXT,
            is_wildcard INTEGER DEFAULT 0,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caller_file_id INTEGER NOT NULL,
            caller_function_id INTEGER,
            callee_name TEXT NOT NULL,
            callee_file_path TEXT,
            line_number INTEGER,
            FOREIGN KEY (caller_file_id) REFERENCES files(id) ON DELETE CASCADE,
            FOREIGN KEY (caller_function_id) REFERENCES functions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_functions_file ON functions(file_id);
        CREATE INDEX IF NOT EXISTS idx_classes_file ON classes(file_id);
        CREATE INDEX IF NOT EXISTS idx_properties_file ON properties(file_id);
        CREATE INDEX IF NOT EXISTS idx_properties_class ON properties(class_id);
        CREATE INDEX IF NOT EXISTS idx_imports_file ON imports(file_id);
        CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_file_id);
        CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee_name);
        """
        conn.executescript(schema)
        conn.commit()

    def compute_file_hash(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_file_hash(self, file_path: str) -> Optional[str]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT hash FROM files WHERE path = ?",
            (file_path,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_file_by_path(self, path: str) -> Optional[FileInfo]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT id, path, hash, modified, last_parsed FROM files WHERE path = ?",
            (path,)
        )
        row = cursor.fetchone()
        return FileInfo.from_db_row(row) if row else None

    def file_needs_update(self, file_path: str) -> bool:
        current_hash = self.compute_file_hash(file_path)
        old_hash = self.get_file_hash(file_path)
        return current_hash != old_hash

    def insert_file(self, path: str, hash_value: str, modified: int) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT OR REPLACE INTO files (path, hash, modified, last_parsed)
               VALUES (?, ?, ?, ?)""",
            (path, hash_value, modified, int(time.time()))
        )
        conn.commit()
        return cursor.lastrowid

    def update_file_hash(self, file_id: int, hash_value: str, modified: int):
        conn = self._get_conn()
        conn.execute(
            """UPDATE files SET hash = ?, modified = ?, last_parsed = ?
               WHERE id = ?""",
            (hash_value, modified, int(time.time()), file_id)
        )
        conn.commit()

    def get_file_id(self, path: str) -> Optional[int]:
        conn = self._get_conn()
        cursor = conn.execute("SELECT id FROM files WHERE path = ?", (path,))
        row = cursor.fetchone()
        return row[0] if row else None

    def delete_file_data(self, file_id: int):
        conn = self._get_conn()
        conn.execute("DELETE FROM functions WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM classes WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM interfaces WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM properties WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM imports WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM calls WHERE caller_file_id = ?", (file_id,))

    def insert_parsed_data(self, file_id: int, parsed: ParsedFile):
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT id, name FROM functions WHERE file_id = ?",
            (file_id,)
        )
        func_map = {name: fid for fid, name in cursor.fetchall()}

        for func in parsed.functions:
            cursor = conn.execute(
                """INSERT INTO functions 
                   (file_id, name, return_type, params, modifiers, start_line, end_line, doc_comment)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                func.to_db_tuple(file_id)
            )
            func_map[func.name] = cursor.lastrowid

        for cls in parsed.classes:
            cursor = conn.execute(
                """INSERT INTO classes
                   (file_id, name, extends, implements, modifiers, start_line, end_line, doc_comment)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                cls.to_db_tuple(file_id)
            )
            class_id = cursor.lastrowid
            for prop in parsed.properties:
                if prop.class_id is None:
                    conn.execute(
                        """INSERT INTO properties
                           (file_id, class_id, name, type, modifiers, default_value)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (file_id, class_id, prop.name, prop.type,
                         json.dumps(prop.modifiers, ensure_ascii=False),
                         prop.default_value)
                    )

        for imp in parsed.imports:
            conn.execute(
                """INSERT INTO imports
                   (file_id, import_path, import_type, is_wildcard)
                   VALUES (?, ?, ?, ?)""",
                imp.to_db_tuple(file_id)
            )

        for call in parsed.calls:
            func_id = func_map.get(call.callee_name) if call.callee_name in func_map else None
            conn.execute(
                """INSERT INTO calls
                   (caller_file_id, caller_function_id, callee_name, callee_file_path, line_number)
                   VALUES (?, ?, ?, ?, ?)""",
                (file_id, func_id, call.callee_name, call.callee_file_path, call.line_number)
            )

        conn.commit()

    def full_scan(self, root_dir: str, file_pattern: str = "**/*.ets") -> dict:
        root = Path(root_dir)
        files = list(root.glob(file_pattern))
        total = len(files)
        results = {
            "total": total,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        logger.info("full_scan_started", total_files=total, root_dir=root_dir)

        for i, file_path in enumerate(files, 1):
            try:
                if self.get_file_id(str(file_path)):
                    results["skipped"] += 1
                    continue

                file_hash = self.compute_file_hash(str(file_path))
                modified = int(file_path.stat().st_mtime)
                file_id = self.insert_file(str(file_path), file_hash, modified)
                results["success"] += 1

                if i % 10 == 0:
                    logger.info("full_scan_progress", processed=i, total=total)

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"file": str(file_path), "error": str(e)})
                logger.error("full_scan_file_error", file=str(file_path), error=str(e))

        logger.info("full_scan_completed", **results)
        return results

    def get_functions_in_file(self, file_id: int) -> list[FunctionInfo]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM functions WHERE file_id = ?",
            (file_id,)
        )
        functions = []
        for row in cursor.fetchall():
            functions.append(FunctionInfo(
                name=row[2],
                return_type=row[3],
                params=json.loads(row[4]) if row[4] else [],
                modifiers=json.loads(row[5]) if row[5] else [],
                start_line=row[6],
                end_line=row[7],
                doc_comment=row[8]
            ))
        return functions

    def get_classes_in_file(self, file_id: int) -> list[ClassInfo]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM classes WHERE file_id = ?",
            (file_id,)
        )
        classes = []
        for row in cursor.fetchall():
            classes.append(ClassInfo(
                name=row[2],
                extends=row[3],
                implements=row[4],
                modifiers=json.loads(row[5]) if row[5] else [],
                start_line=row[6],
                end_line=row[7],
                doc_comment=row[8]
            ))
        return classes

    def get_interfaces_in_file(self, file_id: int) -> list[InterfaceInfo]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM interfaces WHERE file_id = ?",
            (file_id,)
        )
        interfaces = []
        for row in cursor.fetchall():
            interfaces.append(InterfaceInfo(
                name=row[2],
                extends=row[3],
                modifiers=json.loads(row[4]) if row[4] else [],
                start_line=row[5],
                end_line=row[6],
                doc_comment=row[7]
            ))
        return interfaces

    def get_imports_in_file(self, file_id: int) -> list[ImportInfo]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM imports WHERE file_id = ?",
            (file_id,)
        )
        imports = []
        for row in cursor.fetchall():
            imports.append(ImportInfo(
                import_path=row[2],
                import_type=row[3],
                is_wildcard=bool(row[4])
            ))
        return imports

    def get_calls_from_function(self, function_id: int) -> list[CallInfo]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM calls WHERE caller_function_id = ?",
            (function_id,)
        )
        calls = []
        for row in cursor.fetchall():
            calls.append(CallInfo(
                callee_name=row[3],
                callee_file_path=row[4],
                line_number=row[5],
                function_id=row[2]
            ))
        return calls

    def search_symbol(self, name: str) -> dict:
        conn = self._get_conn()
        results = {
            "functions": [],
            "classes": [],
            "interfaces": []
        }

        cursor = conn.execute(
            "SELECT f.id, f.name, f.file_id, fi.path FROM functions f JOIN files fi ON f.file_id = fi.id WHERE f.name LIKE ?",
            (f"%{name}%",)
        )
        for row in cursor.fetchall():
            results["functions"].append({
                "id": row[0],
                "name": row[1],
                "file_id": row[2],
                "file_path": row[3]
            })

        cursor = conn.execute(
            "SELECT c.id, c.name, c.file_id, fi.path FROM classes c JOIN files fi ON c.file_id = fi.id WHERE c.name LIKE ?",
            (f"%{name}%",)
        )
        for row in cursor.fetchall():
            results["classes"].append({
                "id": row[0],
                "name": row[1],
                "file_id": row[2],
                "file_path": row[3]
            })

        cursor = conn.execute(
            "SELECT i.id, i.name, i.file_id, fi.path FROM interfaces i JOIN files fi ON i.file_id = fi.id WHERE i.name LIKE ?",
            (f"%{name}%",)
        )
        for row in cursor.fetchall():
            results["interfaces"].append({
                "id": row[0],
                "name": row[1],
                "file_id": row[2],
                "file_path": row[3]
            })

        return results

    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            delattr(self._local, 'conn')
        logger.info("database_closed", db_path=self.db_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
