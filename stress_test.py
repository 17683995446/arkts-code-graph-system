#!/usr/bin/env python3
import sys
import os
import time
import random
import string
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser


def generate_random_string(length: int = 10) -> str:
    return ''.join(random.choices(string.ascii_letters, k=length))


def generate_test_arkts_file(file_path: Path, complexity: str = 'medium'):
    num_functions = {'simple': 2, 'medium': 5, 'complex': 10}[complexity]
    num_classes = {'simple': 1, 'medium': 2, 'complex': 4}[complexity]
    
    content = []
    
    content.append('// Auto-generated test file')
    content.append(f'// Generated at: {datetime.now()}')
    content.append('')
    
    for i in range(num_classes):
        class_name = f'TestClass{generate_random_string(4)}'
        content.append('')
        content.append('@Component')
        content.append(f'struct {class_name} {{')
        content.append(f'    @State private var count: number = 0')
        content.append('')
        content.append('    build() {')
        content.append('        Column() {')
        content.append('            Text(this.count.toString())')
        content.append('        }')
        content.append('    }')
        content.append('')
        content.append(f'    private func{generate_random_string(3)}(): void {{')
        content.append('        this.count++')
        content.append('    }')
        content.append('}')
    
    for i in range(num_functions):
        func_name = f'func{generate_random_string(5)}'
        return_type = random.choice(['string', 'number', 'void', 'boolean'])
        param_count = random.randint(0, 3)
        params = []
        for j in range(param_count):
            param_type = random.choice(['string', 'number', 'any'])
            params.append(f'p{j}: {param_type}')
        
        content.append('')
        content.append(f'export function {func_name}({", ".join(params)}): {return_type} {{')
        if return_type == 'string':
            content.append(f'    return "Hello from {func_name}"')
        elif return_type == 'number':
            content.append('    return 42')
        elif return_type == 'boolean':
            content.append('    return true')
        else:
            content.append('    // No return value')
        content.append('}')
    
    content.append('')
    content.append('export interface TestInterface {')
    content.append('    name: string')
    content.append('    value: number')
    content.append('}')
    
    file_path.write_text('\n'.join(content), encoding='utf-8')


class StressTester:
    def __init__(self, test_dir: Path, db_path: Path):
        self.test_dir = test_dir
        self.db_path = db_path
        self.results = []
        self.db = None
        self.updater = None
        
    def setup(self):
        self.test_dir.mkdir(exist_ok=True, parents=True)
        if self.db_path.exists():
            self.db_path.unlink()
        
        self.db = CodeGraphDB(str(self.db_path))
        parser = LocalArkTSParser()
        self.updater = IncrementalUpdater(self.db, parser)
        
    def cleanup(self):
        if self.db:
            self.db.close()
    
    def test_initial_scan(self, num_files: int = 10, complexity: str = 'medium') -> dict:
        print(f"\n=== Testing initial scan with {num_files} {complexity} files ===")
        
        start_time = time.time()
        
        files = []
        for i in range(num_files):
            file_path = self.test_dir / f'test_{i:04d}.ets'
            generate_test_arkts_file(file_path, complexity)
            files.append(file_path)
        
        scan_start = time.time()
        success_count = 0
        errors = []
        
        for file_path in files:
            try:
                result = asyncio.run(self.updater.update_file(str(file_path)))
                if result['status'] == 'success':
                    success_count += 1
            except Exception as e:
                errors.append(str(e))
        
        scan_time = time.time() - scan_start
        total_time = time.time() - start_time
        
        result = {
            'test': 'initial_scan',
            'num_files': num_files,
            'complexity': complexity,
            'total_time': total_time,
            'scan_time': scan_time,
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }
        
        self.results.append(result)
        print(f"✓ Initial scan: {total_time:.2f}s, scanned {success_count}/{num_files} files")
        
        return result
    
    def test_incremental_updates(self, num_changes: int = 20) -> dict:
        print(f"\n=== Testing {num_changes} incremental updates ===")
        
        existing_files = list(self.test_dir.glob('*.ets'))
        if not existing_files:
            print("No existing files to modify")
            return {'test': 'incremental_updates', 'error': 'No files'}
        
        start_time = time.time()
        update_times = []
        success_count = 0
        errors = []
        
        for i in range(num_changes):
            file_to_modify = random.choice(existing_files)
            update_start = time.time()
            
            try:
                content = file_to_modify.read_text(encoding='utf-8')
                content += f'\n// Modification {i} at {datetime.now()}\n'
                file_to_modify.write_text(content, encoding='utf-8')
                
                result = asyncio.run(self.updater.update_file(str(file_to_modify)))
                
                update_time = time.time() - update_start
                update_times.append(update_time)
                
                if result['status'] == 'success':
                    success_count += 1
                
            except Exception as e:
                errors.append(str(e))
        
        total_time = time.time() - start_time
        
        result = {
            'test': 'incremental_updates',
            'num_changes': num_changes,
            'total_time': total_time,
            'avg_update_time': sum(update_times) / len(update_times) if update_times else 0,
            'min_update_time': min(update_times) if update_times else 0,
            'max_update_time': max(update_times) if update_times else 0,
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }
        
        self.results.append(result)
        
        print(f"✓ Incremental updates: {total_time:.2f}s total")
        print(f"  Avg: {result['avg_update_time']:.4f}s, Min: {result['min_update_time']:.4f}s, Max: {result['max_update_time']:.4f}s")
        
        return result
    
    def test_hash_collision_check(self) -> dict:
        print("\n=== Testing hash collision detection ===")
        
        test_file = self.test_dir / 'hash_test.ets'
        test_file.write_text('// Original content', encoding='utf-8')
        
        asyncio.run(self.updater.update_file(str(test_file)))
        
        # Check that no-update case is handled correctly
        start_time = time.time()
        result = asyncio.run(self.updater.update_file(str(test_file)))
        skip_time = time.time() - start_time
        
        success = result['status'] == 'skipped'
        
        # Modify the file
        test_file.write_text('// Modified content', encoding='utf-8')
        start_time = time.time()
        result = asyncio.run(self.updater.update_file(str(test_file)))
        update_time = time.time() - start_time
        
        result_dict = {
            'test': 'hash_collision_check',
            'skip_time': skip_time,
            'update_time': update_time,
            'hash_detection_working': success
        }
        
        self.results.append(result_dict)
        print(f"✓ Hash detection working: {success}")
        
        return result_dict
    
    def test_memory_usage(self) -> dict:
        print("\n=== Testing memory usage ===")
        
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        for complexity in ['simple', 'medium', 'complex']:
            for i in range(10):
                file_path = self.test_dir / f'memory_test_{complexity}_{i}.ets'
                generate_test_arkts_file(file_path, complexity)
                asyncio.run(self.updater.update_file(str(file_path)))
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        result = {
            'test': 'memory_usage',
            'initial_memory_mb': initial_memory / (1024 * 1024),
            'final_memory_mb': final_memory / (1024 * 1024),
            'memory_increase_mb': memory_increase / (1024 * 1024)
        }
        
        self.results.append(result)
        print(f"✓ Memory usage: {result['memory_increase_mb']:.2f}MB increase")
        
        return result
    
    def run_all_tests(self):
        print("=" * 60)
        print("STARTING STRESS TESTS")
        print("=" * 60)
        
        try:
            self.setup()
            
            # Test 1: Small scan
            self.test_initial_scan(num_files=5, complexity='simple')
            
            # Test 2: Medium scan
            self.test_initial_scan(num_files=20, complexity='medium')
            
            # Test 3: Incremental updates
            self.test_incremental_updates(num_changes=30)
            
            # Test 4: Hash collision check
            self.test_hash_collision_check()
            
            # Test 5: Memory usage
            self.test_memory_usage()
            
        finally:
            self.cleanup()
            
        self.print_summary()
    
    def print_summary(self):
        print("\n" + "=" * 60)
        print("STRESS TEST SUMMARY")
        print("=" * 60)
        
        for result in self.results:
            print(f"\n{result['test'].upper()}:")
            for k, v in result.items():
                if k == 'test':
                    continue
                if k == 'errors' and v:
                    print(f"  Errors: {len(v)} errors (first 3: {v[:3]})")
                elif isinstance(v, float):
                    print(f"  {k}: {v:.4f}")
                else:
                    print(f"  {k}: {v}")


import asyncio


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        print("Running quick test...")
        test_dir = Path('/tmp/codegraph_stress_test')
        db_path = Path('/tmp/codegraph_stress.db')
    else:
        test_dir = Path(__file__).parent / 'stress_test_dir'
        db_path = Path(__file__).parent / 'stress_test.db'
    
    tester = StressTester(test_dir, db_path)
    tester.run_all_tests()
    

if __name__ == '__main__':
    main()
