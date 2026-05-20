#!/usr/bin/env python3
import sys
import asyncio
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser


def test_basic_functionality():
    print("=== Testing basic functionality ===")
    
    # Cleanup
    db_path = Path('test.db')
    if db_path.exists():
        db_path.unlink()
    
    print("1. Initializing database...")
    db = CodeGraphDB(str(db_path))
    parser = LocalArkTSParser()
    updater = IncrementalUpdater(db, parser)
    
    print("2. Testing with example file...")
    test_file = Path('test-arkts-project/src/Index.ets')
    if not test_file.exists():
        test_file = Path('example-project/Index.ets')
    
    if test_file.exists():
        print(f"   Testing file: {test_file}")
        result = asyncio.run(updater.update_file(str(test_file)))
        print(f"   Result: {result['status']}")
        
        if 'error' in result:
            print(f"   Error: {result['error']}")
        
        print(f"   Parsed data: {result.get('parsed', {})}")
        
        # Check database
        file_id = db.get_file_id(str(test_file))
        print(f"   File ID in DB: {file_id}")
        
        if file_id:
            classes = db.get_classes_in_file(file_id)
            print(f"   Classes found: {len(classes)}")
            for cls in classes:
                print(f"     - {cls.name}")
            
            functions = db.get_functions_in_file(file_id)
            print(f"   Functions found: {len(functions)}")
            for func in functions:
                print(f"     - {func.name}")
    else:
        print("   No test file found!")
        return False
    
    print("\n3. Testing hash detection...")
    hash1 = db.compute_file_hash(str(test_file))
    print(f"   Original hash: {hash1[:16]}...")
    
    # Modify the file temporarily
    original_content = test_file.read_text()
    test_file.write_text(original_content + '\n// Test modification')
    
    hash2 = db.compute_file_hash(str(test_file))
    print(f"   Modified hash: {hash2[:16]}...")
    print(f"   Hash changed: {hash1 != hash2}")
    
    # Test update
    result = asyncio.run(updater.update_file(str(test_file)))
    print(f"   Update status after modification: {result['status']}")
    
    # Restore
    test_file.write_text(original_content)
    
    print("\n4. Testing multiple file scan...")
    test_dir = Path('test-arkts-project/src')
    if not test_dir.exists():
        test_dir = Path('example-project')
    
    ets_files = list(test_dir.rglob('*.ets'))
    print(f"   Found {len(ets_files)} .ets files")
    
    success_count = 0
    for ets_file in ets_files:
        try:
            result = asyncio.run(updater.update_file(str(ets_file)))
            if result['status'] == 'success':
                success_count += 1
        except Exception as e:
            print(f"   Error scanning {ets_file}: {e}")
    
    print(f"   Successfully scanned: {success_count}/{len(ets_files)}")
    
    print("\n5. Testing statistics...")
    cursor = db.conn.execute("SELECT COUNT(*) FROM files")
    file_count = cursor.fetchone()[0]
    print(f"   Total files: {file_count}")
    
    cursor = db.conn.execute("SELECT COUNT(*) FROM functions")
    func_count = cursor.fetchone()[0]
    print(f"   Total functions: {func_count}")
    
    cursor = db.conn.execute("SELECT COUNT(*) FROM classes")
    class_count = cursor.fetchone()[0]
    print(f"   Total classes: {class_count}")
    
    db.close()
    db_path.unlink()
    
    print("\n=== Basic test completed ===")
    return True


def test_parser():
    print("\n=== Testing parser directly ===")
    
    parser = LocalArkTSParser()
    
    test_code = '''
function testFunction(a: number, b: string): boolean {
    return true
}

@Component
struct TestComponent {
    build() {
        Column() {}
    }
}

export interface TestInterface {
    name: string
}
'''
    
    result = parser.parse_content(test_code, 'test.ets')
    
    print(f"Functions: {len(result.functions)}")
    for func in result.functions:
        print(f"  - {func.name}")
    
    print(f"Classes: {len(result.classes)}")
    for cls in result.classes:
        print(f"  - {cls.name}")
    
    print(f"Interfaces: {len(result.interfaces)}")
    for iface in result.interfaces:
        print(f"  - {iface.name}")


if __name__ == '__main__':
    try:
        test_parser()
        success = test_basic_functionality()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
