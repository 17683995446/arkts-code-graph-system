from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any

# Add parent path to import our existing modules
sys.path.append(str(Path(__file__).parent.parent))

from src.database import CodeGraphDB
from src.parser import LocalArkTSParser
from src.incremental import IncrementalUpdater
from src.watcher import FileWatcher

app = FastAPI(title="ArkTS Code Knowledge Graph")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
db_instance: CodeGraphDB = None
updater_instance: IncrementalUpdater = None
watcher_instance: FileWatcher = None
active_watcher: bool = False
update_logs: List[Dict] = []
connected_clients: List[WebSocket] = []

def init_db():
    global db_instance, updater_instance
    db_path = Path(__file__).parent.parent / "code_graph.db"
    db_instance = CodeGraphDB(str(db_path))
    parser = LocalArkTSParser()
    updater_instance = IncrementalUpdater(db_instance, parser)
    print("Database initialized")

@app.on_event("startup")
async def startup():
    init_db()

@app.on_event("shutdown")
async def shutdown():
    global watcher_instance
    if watcher_instance:
        watcher_instance.stop()
    if db_instance:
        db_instance.close()

async def broadcast_log(log_entry: Dict):
    update_logs.append(log_entry)
    if len(update_logs) > 100:
        update_logs.pop(0)
    
    for client in connected_clients:
        try:
            await client.send_json(log_entry)
        except:
            pass

def on_file_changed(file_path: str):
    asyncio.create_task(handle_file_update(file_path))

async def handle_file_update(file_path: str):
    log_entry = {
        "timestamp": int(asyncio.get_event_loop().time()),
        "type": "update",
        "file": file_path,
        "status": "started"
    }
    await broadcast_log(log_entry)
    
    try:
        result = await updater_instance.update_file(file_path)
        log_entry = {
            "timestamp": int(asyncio.get_event_loop().time()),
            "type": "update",
            "file": file_path,
            "status": result["status"],
            "duration": result.get("duration", 0),
            "parsed": result.get("parsed", {})
        }
    except Exception as e:
        log_entry = {
            "timestamp": int(asyncio.get_event_loop().time()),
            "type": "update",
            "file": file_path,
            "status": "error",
            "error": str(e)
        }
    
    await broadcast_log(log_entry)

@app.get("/api/project/stats")
async def get_stats():
    if not db_instance:
        return {"error": "Database not initialized"}
    
    cursor = db_instance.conn.execute("SELECT COUNT(*) FROM files")
    file_count = cursor.fetchone()[0]
    
    cursor = db_instance.conn.execute("SELECT COUNT(*) FROM functions")
    function_count = cursor.fetchone()[0]
    
    cursor = db_instance.conn.execute("SELECT COUNT(*) FROM classes")
    class_count = cursor.fetchone()[0]
    
    cursor = db_instance.conn.execute("SELECT COUNT(*) FROM interfaces")
    interface_count = cursor.fetchone()[0]
    
    cursor = db_instance.conn.execute("SELECT MAX(last_parsed) FROM files")
    last_parsed = cursor.fetchone()[0]
    
    return {
        "files": file_count,
        "functions": function_count,
        "classes": class_count,
        "interfaces": interface_count,
        "last_parsed": last_parsed,
        "watching": active_watcher
    }

@app.post("/api/project/scan")
async def scan_project(root_dir: str = "/workspace/example-project"):
    if not db_instance or not updater_instance:
        return {"error": "System not initialized"}
    
    log_entry = {
        "timestamp": int(asyncio.get_event_loop().time()),
        "type": "scan",
        "status": "started"
    }
    await broadcast_log(log_entry)
    
    results = {
        "total": 0,
        "success": 0,
        "failed": 0
    }
    
    root = Path(root_dir)
    if not root.exists():
        return {"error": "Directory not found"}
    
    files = list(root.glob("**/*.ets"))
    results["total"] = len(files)
    
    for file_path in files:
        try:
            result = await updater_instance.update_file(str(file_path))
            if result["status"] == "success":
                results["success"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            results["failed"] += 1
            print(f"Error scanning {file_path}: {e}")
    
    log_entry = {
        "timestamp": int(asyncio.get_event_loop().time()),
        "type": "scan",
        "status": "completed",
        "results": results
    }
    await broadcast_log(log_entry)
    
    return results

@app.get("/api/project/files")
async def get_files():
    if not db_instance:
        return {"files": []}
    
    cursor = db_instance.conn.execute(
        "SELECT id, path, modified, last_parsed FROM files ORDER BY path"
    )
    files = []
    for row in cursor.fetchall():
        files.append({
            "id": row[0],
            "path": row[1],
            "modified": row[2],
            "last_parsed": row[3]
        })
    return {"files": files}

@app.get("/api/files/{file_id}")
async def get_file(file_id: int):
    if not db_instance:
        return {"error": "Database not initialized"}
    
    cursor = db_instance.conn.execute(
        "SELECT id, path, hash, modified, last_parsed FROM files WHERE id = ?",
        (file_id,)
    )
    row = cursor.fetchone()
    if not row:
        return {"error": "File not found"}
    
    file_info = {
        "id": row[0],
        "path": row[1],
        "hash": row[2],
        "modified": row[3],
        "last_parsed": row[4]
    }
    
    return file_info

@app.get("/api/files/{file_id}/functions")
async def get_file_functions(file_id: int):
    if not db_instance:
        return {"functions": []}
    
    functions = db_instance.get_functions_in_file(file_id)
    return {"functions": [
        {
            "id": f.id if hasattr(f, 'id') else None,
            "name": f.name,
            "return_type": f.return_type,
            "params": f.params,
            "modifiers": f.modifiers,
            "start_line": f.start_line,
            "end_line": f.end_line
        }
        for f in functions
    ]}

@app.get("/api/files/{file_id}/classes")
async def get_file_classes(file_id: int):
    if not db_instance:
        return {"classes": []}
    
    classes = db_instance.get_classes_in_file(file_id)
    return {"classes": [
        {
            "id": c.id if hasattr(c, 'id') else None,
            "name": c.name,
            "extends": c.extends,
            "implements": c.implements,
            "modifiers": c.modifiers,
            "start_line": c.start_line,
            "end_line": c.end_line
        }
        for c in classes
    ]}

@app.get("/api/search")
async def search_symbols(q: str):
    if not db_instance:
        return {"functions": [], "classes": [], "interfaces": []}
    
    results = db_instance.search_symbol(q)
    return results

@app.get("/api/watch/status")
async def get_watch_status():
    return {"watching": active_watcher}

@app.post("/api/watch/start")
async def start_watch(root_dir: str = "/workspace/example-project"):
    global watcher_instance, active_watcher
    
    if not updater_instance:
        return {"error": "System not initialized"}
    
    if active_watcher:
        return {"error": "Already watching"}
    
    watcher_instance = FileWatcher(
        root_dir=root_dir,
        callback=on_file_changed,
        exclude_patterns=["**/node_modules/**", "**/.arkui/**", "**/build/**"]
    )
    watcher_instance.start()
    active_watcher = True
    
    log_entry = {
        "timestamp": int(asyncio.get_event_loop().time()),
        "type": "watch",
        "status": "started"
    }
    await broadcast_log(log_entry)
    
    return {"status": "started"}

@app.post("/api/watch/stop")
async def stop_watch():
    global watcher_instance, active_watcher
    
    if not active_watcher:
        return {"error": "Not watching"}
    
    if watcher_instance:
        watcher_instance.stop()
        watcher_instance = None
    
    active_watcher = False
    
    log_entry = {
        "timestamp": int(asyncio.get_event_loop().time()),
        "type": "watch",
        "status": "stopped"
    }
    await broadcast_log(log_entry)
    
    return {"status": "stopped"}

@app.get("/api/watch/logs")
async def get_logs():
    return {"logs": update_logs}

@app.get("/api/graph/nodes")
async def get_graph_nodes():
    if not db_instance:
        return {"nodes": []}
    
    nodes = []
    
    cursor = db_instance.conn.execute("SELECT id, name, file_id FROM classes")
    for row in cursor.fetchall():
        nodes.append({
            "id": f"class_{row[0]}",
            "label": row[1],
            "type": "class",
            "file_id": row[2]
        })
    
    cursor = db_instance.conn.execute("SELECT id, name, file_id FROM functions")
    for row in cursor.fetchall():
        nodes.append({
            "id": f"func_{row[0]}",
            "label": row[1],
            "type": "function",
            "file_id": row[2]
        })
    
    cursor = db_instance.conn.execute("SELECT id, name, file_id FROM interfaces")
    for row in cursor.fetchall():
        nodes.append({
            "id": f"iface_{row[0]}",
            "label": row[1],
            "type": "interface",
            "file_id": row[2]
        })
    
    return {"nodes": nodes}

@app.get("/api/graph/edges")
async def get_graph_edges():
    if not db_instance:
        return {"edges": []}
    
    edges = []
    
    cursor = db_instance.conn.execute(
        "SELECT id, caller_function_id, callee_name, line_number FROM calls"
    )
    for row in cursor.fetchall():
        edges.append({
            "id": f"call_{row[0]}",
            "source": f"func_{row[1]}" if row[1] else None,
            "target": None,
            "label": row[2],
            "type": "calls"
        })
    
    return {"edges": edges}

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

# Serve static frontend
dist_path = Path(__file__).parent / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
