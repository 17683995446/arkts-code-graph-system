#!/usr/bin/env python3
"""
极端边界场景测试套件
测试系统在极端条件下的表现
"""
import os
import sys
import time
import random
import tempfile
import threading
import asyncio
from pathlib import Path
from datetime import datetime
import structlog

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

logger = structlog.get_logger()


class ExtremeBoundaryTester:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.db_path = Path(tempfile.mktemp(suffix='.db'))
        self.db = None
        self.parser = None
        self.updater = None
        self.errors = []
        self.warnings = []
        self.test_results = {}
        self.start_time = None
        
    def setup(self):
        logger.info("extreme_boundary_test_setup", db_path=self.db_path)
        self.db = CodeGraphDB(str(self.db_path))
        self.parser = LocalArkTSParser()
        self.updater = IncrementalUpdater(self.db, self.parser)
        self.start_time = time.time()
        
    def teardown(self):
        if self.db:
            self.db.close()
        if self.db_path.exists():
            self.db_path.unlink()
        logger.info("extreme_boundary_test_teardown")
        
    def test_deep_recursion_files(self):
        """测试深层嵌套文件结构"""
        print("\n" + "="*80)
        print("Test 1: 深层嵌套文件结构测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            deep_path = self.project_path / "deep" / "level1" / "level2" / "level3" / "level4" / "level5"
            deep_path.mkdir(parents=True, exist_ok=True)
            
            for i in range(20):
                temp_file = deep_path / f"nested_{i}.ets"
                temp_file.write_text(f"""export function nested{i}() {{ return {i}; }}""")
                
                result = asyncio.run(self.updater.update_file(str(temp_file)))
                
                if result['status'] != 'success':
                    errors.append(f"Nested {i}: {result['error']}")
                
                temp_file.unlink()
            
            import shutil
            (self.project_path / "deep").parent.rmtree()
            
            if errors:
                print(f"✗ 深层嵌套测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 深层嵌套文件结构测试通过 (20个文件)")
                
        except Exception as e:
            print(f"✗ 深层嵌套测试失败: {e}")
            success = False
        
        self.test_results['deep_recursion_files'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_extreme_filename_lengths(self):
        """测试极端文件名的长度"""
        print("\n" + "="*80)
        print("Test 2: 极端文件名长度测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            test_cases = [
                ("short", "a.ets"),
                ("normal", "normal_filename.ets"),
                ("long_100", "a" * 100 + ".ets"),
                ("very_long_255", "a" * 255 + ".ets"),
            ]
            
            for name, filename in test_cases:
                try:
                    temp_file = self.project_path / filename
                    temp_file.write_text(f"""export function {name}() {{ return true; }}""")
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    print(f"{name} ({len(filename)} chars): {result['status']}")
                    
                    if result['status'] != 'success':
                        errors.append(f"{name}: {result['error']}")
                    
                    temp_file.unlink()
                    
                except Exception as e:
                    print(f"✗ {name} 异常: {e}")
                    errors.append(f"{name}: {str(e)}")
            
            if errors:
                print(f"✗ 极端文件名长度测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 极端文件名长度测试通过")
                
        except Exception as e:
            print(f"✗ 极端文件名长度测试失败: {e}")
            success = False
        
        self.test_results['extreme_filename_lengths'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_simultaneous_read_write_lock(self):
        """测试同时读写锁竞争"""
        print("\n" + "="*80)
        print("Test 3: 同时读写锁竞争测试")
        print("="*80)
        
        success = True
        errors = []
        operations = {'reads': 0, 'writes': 0, 'errors': 0}
        lock = threading.Lock()
        
        def reader_worker(worker_id: int):
            try:
                for _ in range(30):
                    result = self.db.search_symbol("test")
                    with lock:
                        operations['reads'] += 1
            except Exception as e:
                with lock:
                    operations['errors'] += 1
                errors.append(f"Reader {worker_id}: {str(e)}")
        
        def writer_worker(worker_id: int):
            try:
                for i in range(10):
                    temp_file = self.project_path / f"rw_{worker_id}_{i}.ets"
                    temp_file.write_text(f"""export function rw{worker_id}_{i}() {{ return {i}; }}""")
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    with lock:
                        operations['writes'] += 1
                    
                    temp_file.unlink()
            except Exception as e:
                with lock:
                    operations['errors'] += 1
                errors.append(f"Writer {worker_id}: {str(e)}")
        
        try:
            threads = []
            for i in range(10):
                t = threading.Thread(target=reader_worker, args=(i,))
                threads.append(t)
                t.start()
            
            for i in range(5):
                t = threading.Thread(target=writer_worker, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join(timeout=60)
            
            print(f"读取操作: {operations['reads']}, 写入操作: {operations['writes']}, 错误: {operations['errors']}")
            
            if errors or operations['errors'] > 0:
                print(f"✗ 同时读写锁竞争测试失败，发现 {len(errors)} 个错误")
                for err in errors[:5]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 同时读写锁竞争测试通过")
                
        except Exception as e:
            print(f"✗ 同时读写锁竞争测试失败: {e}")
            success = False
        
        self.test_results['simultaneous_read_write_lock'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors[:10]
        }
        return success
        
    def test_mixed_encoding_files(self):
        """测试混合格编码文件"""
        print("\n" + "="*80)
        print("Test 4: 混合格编码文件测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            test_cases = [
                ("utf8_simple", "你好世界", "utf-8"),
                ("utf8_emoji", "Hello 🌍 World 🐱", "utf-8"),
                ("mixed_content", "const 变量 = '测试'; export function 函数() {}", "utf-8"),
                ("cyrillic", "функция тест()", "utf-8"),
                ("arabic", "دالة اختبار()", "utf-8"),
            ]
            
            for name, content, encoding in test_cases:
                try:
                    temp_file = self.project_path / f"encoding_{name}.ets"
                    temp_file.write_text(content, encoding=encoding)
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    print(f"{name}: {result['status']}")
                    
                    if result['status'] != 'success':
                        errors.append(f"{name}: {result['error']}")
                    
                    temp_file.unlink()
                    
                except Exception as e:
                    print(f"✗ {name} 异常: {e}")
                    errors.append(f"{name}: {str(e)}")
            
            if errors:
                print(f"✗ 混合格编码文件测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 混合格编码文件测试通过")
                
        except Exception as e:
            print(f"✗ 混合格编码文件测试失败: {e}")
            success = False
        
        self.test_results['mixed_encoding_files'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_rapid_db_operations(self):
        """测试极速数据库操作"""
        print("\n" + "="*80)
        print("Test 5: 极速数据库操作测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            start = time.time()
            
            for i in range(1000):
                temp_file = self.project_path / f"rapid_{i}.ets"
                temp_file.write_text(f"""export function rapid{i}() {{ return {i}; }}""")
                
                result = asyncio.run(self.updater.update_file(str(temp_file)))
                
                if result['status'] != 'success':
                    errors.append(f"Rapid {i}: {result['error']}")
                
                temp_file.unlink()
                
                if i % 200 == 0:
                    print(f"进度: {i}/1000")
            
            elapsed = time.time() - start
            rate = 1000 / elapsed
            
            print(f"完成: 1000次操作，耗时 {elapsed:.2f}秒，速度 {rate:.2f} ops/sec")
            
            if errors:
                print(f"✗ 极速数据库操作测试失败，发现 {len(errors)} 个错误")
                for err in errors[:5]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 极速数据库操作测试通过")
                
        except Exception as e:
            print(f"✗ 极速数据库操作测试失败: {e}")
            success = False
        
        self.test_results['rapid_db_operations'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors[:10]
        }
        return success
        
    def run_all_tests(self):
        self.setup()
        
        print("🚀 开始极端边界场景测试...")
        print(f"测试项目: {self.project_path}")
        print(f"开始时间: {datetime.now().isoformat()}")
        
        tests = [
            self.test_deep_recursion_files,
            self.test_extreme_filename_lengths,
            self.test_simultaneous_read_write_lock,
            self.test_mixed_encoding_files,
            self.test_rapid_db_operations,
        ]
        
        for test in tests:
            test_name = test.__name__
            try:
                test()
            except Exception as e:
                print(f"✗ 测试 {test_name} 执行异常: {e}")
                import traceback
                traceback.print_exc()
                self.test_results[test_name] = {
                    'success': False,
                    'error': str(e)
                }
        
        print("\n" + "="*80)
        print("📊 极端边界场景测试总结")
        print("="*80)
        
        passed = sum(1 for v in self.test_results.values() if v.get('success', False))
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✓ PASSED" if result.get('success', False) else "✗ FAILED"
            errors = result.get('errors', 0)
            print(f"  {test_name}: {status} ({errors} errors)")
        
        print(f"\n总测试: {total}, 通过: {passed}, 失败: {total - passed}")
        
        total_errors = sum(len(r.get('error_list', [])) for r in self.test_results.values())
        if total_errors > 0:
            print(f"\n📋 所有错误列表 (共 {total_errors} 个):")
            for test_name, result in self.test_results.items():
                if result.get('error_list'):
                    print(f"\n  [{test_name}]")
                    for error in result['error_list'][:3]:
                        print(f"    - {error}")
        
        elapsed = time.time() - self.start_time
        print(f"\n总耗时: {elapsed:.2f} 秒")
        
        return passed == total


if __name__ == "__main__":
    tester = ExtremeBoundaryTester("large-test-project")
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
