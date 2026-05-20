import pytest
import tempfile
import os
from pathlib import Path

from src.database import CodeGraphDB
from src.models import FunctionInfo, ClassInfo, ParsedFile


class TestCodeGraphDB:
    @pytest.fixture
    def db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = CodeGraphDB(path)
        yield db
        db.close()
        os.unlink(path)

    @pytest.fixture
    def sample_file(self, tmp_path):
        file_path = tmp_path / "test.ets"
        file_path.write_text("""
@Entry
@Component
struct Index {
  @State message: string = 'Hello'

  build() {
    Column() {
      Text(this.message)
    }
  }

  private getData(): string {
    return fetchData()
  }
}

function fetchData(): string {
  return "data"
}
""")
        return str(file_path)

    def test_init_creates_tables(self, db):
        cursor = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "files" in tables
        assert "functions" in tables
        assert "classes" in tables
        assert "interfaces" in tables
        assert "properties" in tables
        assert "imports" in tables
        assert "calls" in tables

    def test_compute_file_hash(self, db, sample_file):
        hash1 = db.compute_file_hash(sample_file)
        assert hash1 is not None
        assert len(hash1) == 64
        
        hash2 = db.compute_file_hash(sample_file)
        assert hash1 == hash2

    def test_hash_changes_on_content(self, db, sample_file):
        hash1 = db.compute_file_hash(sample_file)
        
        with open(sample_file, "a") as f:
            f.write("\n// comment")
        
        hash2 = db.compute_file_hash(sample_file)
        assert hash1 != hash2

    def test_insert_file(self, db, sample_file):
        hash_val = db.compute_file_hash(sample_file)
        modified = int(Path(sample_file).stat().st_mtime)
        
        file_id = db.insert_file(sample_file, hash_val, modified)
        assert file_id is not None
        assert file_id > 0
        
        stored_hash = db.get_file_hash(sample_file)
        assert stored_hash == hash_val

    def test_get_file_id(self, db, sample_file):
        hash_val = db.compute_file_hash(sample_file)
        modified = int(Path(sample_file).stat().st_mtime)
        
        file_id = db.insert_file(sample_file, hash_val, modified)
        
        retrieved_id = db.get_file_id(sample_file)
        assert retrieved_id == file_id

    def test_file_needs_update(self, db, sample_file):
        assert db.file_needs_update(sample_file) == True
        
        hash_val = db.compute_file_hash(sample_file)
        modified = int(Path(sample_file).stat().st_mtime)
        db.insert_file(sample_file, hash_val, modified)
        
        assert db.file_needs_update(sample_file) == False

    def test_delete_file_data(self, db, sample_file):
        hash_val = db.compute_file_hash(sample_file)
        modified = int(Path(sample_file).stat().st_mtime)
        file_id = db.insert_file(sample_file, hash_val, modified)
        
        parsed = ParsedFile(
            functions=[FunctionInfo(
                name="testFunc",
                return_type="string"
            )],
            classes=[ClassInfo(name="TestClass")]
        )
        db.insert_parsed_data(file_id, parsed)
        
        db.delete_file_data(file_id)
        
        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM functions WHERE file_id = ?",
            (file_id,)
        )
        assert cursor.fetchone()[0] == 0

    def test_search_symbol(self, db, sample_file):
        hash_val = db.compute_file_hash(sample_file)
        modified = int(Path(sample_file).stat().st_mtime)
        file_id = db.insert_file(sample_file, hash_val, modified)
        
        parsed = ParsedFile(
            functions=[FunctionInfo(name="myFunction", return_type="string")],
            classes=[ClassInfo(name="MyClass")]
        )
        db.insert_parsed_data(file_id, parsed)
        
        results = db.search_symbol("my")
        
        assert len(results["functions"]) == 1
        assert results["functions"][0]["name"] == "myFunction"
        assert len(results["classes"]) == 1
        assert results["classes"][0]["name"] == "MyClass"

    def test_foreign_key_cascade_delete(self, db, sample_file):
        hash_val = db.compute_file_hash(sample_file)
        modified = int(Path(sample_file).stat().st_mtime)
        file_id = db.insert_file(sample_file, hash_val, modified)
        
        parsed = ParsedFile(
            functions=[FunctionInfo(name="testFunc")],
            classes=[ClassInfo(name="TestClass")]
        )
        db.insert_parsed_data(file_id, parsed)
        
        db.conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
        db.conn.commit()
        
        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM functions WHERE file_id = ?",
            (file_id,)
        )
        assert cursor.fetchone()[0] == 0
