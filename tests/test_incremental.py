import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from src.database import CodeGraphDB
from src.parser import ArkTSParser, LocalArkTSParser
from src.incremental import IncrementalUpdater


class TestIncrementalUpdater:
    @pytest.fixture
    def db_setup(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        db = CodeGraphDB(db_path)
        
        yield db, db_path
        
        db.close()
        os.unlink(db_path)

    @pytest.fixture
    def sample_file(self, tmp_path):
        file_path = tmp_path / "TestComponent.ets"
        file_path.write_text("""
@Entry
@Component
struct TestComponent {
  @State count: number = 0

  build() {
    Column() {
      Text(`Count: ${this.count}`)
    }
  }

  increment(): void {
    this.count++
  }
}
""")
        return str(file_path)

    @pytest.mark.asyncio
    async def test_update_new_file(self, db_setup, sample_file):
        db, db_path = db_setup
        
        mock_parser = AsyncMock()
        mock_parser.parse_file.return_value = MagicMock(
            functions=[],
            classes=[],
            interfaces=[],
            properties=[],
            imports=[],
            calls=[]
        )
        
        updater = IncrementalUpdater(db, mock_parser)
        result = await updater.update_file(sample_file)
        
        assert result["status"] == "success"
        assert "duration" in result
        assert result["duration"] >= 0
        assert result["file_path"] == sample_file

    @pytest.mark.asyncio
    async def test_update_skips_unchanged_file(self, db_setup, sample_file):
        db, db_path = db_setup
        
        mock_parser = AsyncMock()
        mock_parser.parse_file.return_value = MagicMock(
            functions=[], classes=[], interfaces=[],
            properties=[], imports=[], calls=[]
        )
        
        updater = IncrementalUpdater(db, mock_parser)
        await updater.update_file(sample_file)
        
        result = await updater.update_file(sample_file)
        
        assert result["status"] == "skipped"
        assert result["error"] == "Hash unchanged"

    @pytest.mark.asyncio
    async def test_update_detects_changes(self, db_setup, sample_file):
        db, db_path = db_setup
        
        mock_parser = AsyncMock()
        mock_parser.parse_file.return_value = MagicMock(
            functions=[], classes=[], interfaces=[],
            properties=[], imports=[], calls=[]
        )
        
        updater = IncrementalUpdater(db, mock_parser)
        await updater.update_file(sample_file)
        
        with open(sample_file, "a") as f:
            f.write("\n// Modified")
        
        result = await updater.update_file(sample_file)
        
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_update_nonexistent_file(self, db_setup):
        db, db_path = db_setup
        
        mock_parser = AsyncMock()
        updater = IncrementalUpdater(db, mock_parser)
        
        result = await updater.update_file("/nonexistent/file.ets")
        
        assert result["status"] == "failed"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_batch_update(self, db_setup, tmp_path):
        db, db_path = db_setup
        
        mock_parser = AsyncMock()
        mock_parser.parse_file.return_value = MagicMock(
            functions=[], classes=[], interfaces=[],
            properties=[], imports=[], calls=[]
        )
        
        updater = IncrementalUpdater(db, mock_parser)
        
        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.ets"
            f.write_text(f"""
struct Component{i} {{
  value: number = {i}
}}
""")
            files.append(str(f))
        
        results = await updater.batch_update(files)
        
        assert results["total"] == 3
        assert results["success"] == 3
        assert results["failed"] == 0
        assert results["skipped"] == 0


class TestIncrementalUpdaterWithLocalParser:
    @pytest.fixture
    def db_setup(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        db = CodeGraphDB(db_path)
        
        yield db, db_path
        
        db.close()
        os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_update_with_local_parser(self, db_setup):
        db, db_path = db_setup
        
        local_parser = LocalArkTSParser()
        updater = IncrementalUpdater(db, local_parser)
        
        fd, temp_file = tempfile.mkstemp(suffix=".ets")
        os.write(fd, b"""
@Component
struct MyComponent {
  build() {
    Column() {}
  }
}
""")
        os.close(fd)
        
        result = await updater.update_file(temp_file)
        
        assert result["status"] == "success"
        assert result.get("parsed", {}).get("classes") == 1
        
        os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_hash_changes_after_content_change(self, db_setup):
        db, db_path = db_setup
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ets', delete=False) as f:
            f.write("""
struct Original {
  value: number
}
""")
            temp_file = f.name
        
        local_parser = LocalArkTSParser()
        updater = IncrementalUpdater(db, local_parser)
        
        result1 = await updater.update_file(temp_file)
        assert result1["status"] == "success"
        
        with open(temp_file, "r") as f:
            content = f.read()
        with open(temp_file, "w") as f:
            f.write(content.replace("Original", "Modified"))
        
        result2 = await updater.update_file(temp_file)
        assert result2["status"] == "success"
        
        file_id = db.get_file_id(temp_file)
        classes = db.get_classes_in_file(file_id)
        assert classes[0].name == "Modified"
        
        os.unlink(temp_file)


class TestIncrementalUpdaterSync:
    @pytest.fixture
    def updater_components(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        db = CodeGraphDB(db_path)
        parser = AsyncMock()
        updater = IncrementalUpdater(db, parser)
        
        yield updater, db_path
        
        db.close()
        os.unlink(db_path)

    def test_update_file_sync(self, updater_components):
        updater, db_path = updater_components
        
        fd, temp_file = tempfile.mkstemp(suffix=".ets")
        os.write(fd, b"struct Test {}")
        os.close(fd)
        
        with patch.object(updater, 'update_file', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = {
                "status": "success",
                "duration": 0.1,
                "file_path": temp_file
            }
            result = updater.update_file_sync(temp_file)
        
        assert result is not None
        assert "status" in result
        assert "duration" in result
        
        os.unlink(temp_file)
