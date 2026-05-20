#!/usr/bin/env python3
"""
精简版高级真实场景压力测试
专注测试关键场景和边界情况
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
from typing import Dict, List, Any
import structlog

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

logger = structlog.get_logger()


class FocusedStressTester:
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
        logger.info("focused_stress_test_setup", db_path=self.db_path)
        self.db = CodeGraphDB(str(self.db_path))
        self.parser = LocalArkTSParser()
        self.updater = IncrementalUpdater(self.db, self.parser)
        self.start_time = time.time()
        
    def teardown(self):
        if self.db:
            self.db.close()
        if self.db_path.exists():
            self.db_path.unlink()
        logger.info("focused_stress_test_teardown")
        
    def test_high_concurrency(self):
        """测试高并发写入（50线程）"""
        print("\n" + "="*80)
        print("Test 1: 高并发写入测试 (50线程)")
        print("="*80)
        
        success = True
        errors = []
        files = list(self.project_path.glob("**/*.ets"))[:10]
        completed = {'count': 0, 'lock': threading.Lock()}
        
        def concurrent_worker(worker_id: int):
            try:
                for iteration in range(5):
                    file_path = files[worker_id % len(files)]
                    content = f"""export function wf{worker_id}_{iteration}() {{
    return {worker_id * iteration};
}}"""
                    temp_file = self.project_path / f"concurrent_{worker_id}_{iteration}.ets"
                    temp_file.write_text(content)
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    if result['status'] != 'success':
                        errors.append(f"Worker {worker_id} iter {iteration}: {result['error']}")
                    
                    temp_file.unlink()
                    
                    with completed['lock']:
                        completed['count'] += 1
                        
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
        
        try:
            threads = []
            for i in range(50):
                t = threading.Thread(target=concurrent_worker, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join(timeout=60)
            
            print(f"完成操作: {completed['count']}/250")
            
            if errors:
                print(f"✗ 高并发测试失败，发现 {len(errors)} 个错误:")
                for err in errors[:10]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 高并发写入测试通过 (250次操作完成)")
                
        except Exception as e:
            print(f"✗ 高并发测试失败: {e}")
            success = False
        
        self.test_results['high_concurrency'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors[:10]
        }
        return success
        
    def test_binary_file_handling(self):
        """测试二进制文件处理（发现问题！）"""
        print("\n" + "="*80)
        print("Test 2: 二进制文件处理测试（关键！）")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            test_cases = [
                ("binary_data", b"\x00\x01\x02\xff\xfe\xfd"),
                ("invalid_utf8_1", b"\xc0\x80\xe0\x80"),
                ("invalid_utf8_2", b"\xfe\xff\xfe\xff"),
            ]
            
            for name, content in test_cases:
                try:
                    temp_file = self.project_path / f"binary_{name}.ets"
                    temp_file.write_bytes(content)
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    print(f"{name}: {result['status']}")
                    
                    if result['status'] == 'error':
                        print(f"  错误: {result['error']}")
                        errors.append(f"{name}: {result['error']}")
                    
                    temp_file.unlink()
                    
                except Exception as e:
                    print(f"✗ {name} 异常: {e}")
                    errors.append(f"{name}: {str(e)}")
            
            if errors:
                print(f"\n⚠ 发现 {len(errors)} 个二进制文件处理问题:")
                for err in errors:
                    print(f"  - {err}")
                print("\n💡 这是一个需要修复的bug！系统无法处理二进制文件")
                success = False
            else:
                print("\n✓ 二进制文件处理测试通过")
                
        except Exception as e:
            print(f"✗ 二进制文件处理测试失败: {e}")
            success = False
        
        self.test_results['binary_file_handling'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_database_query_under_load(self):
        """测试高负载下的数据库查询"""
        print("\n" + "="*80)
        print("Test 3: 高负载数据库查询测试")
        print("="*80)
        
        success = True
        errors = []
        query_results = []
        
        def populate_worker(worker_id: int):
            try:
                for i in range(50):
                    temp_file = self.project_path / f"populate_{worker_id}_{i}.ets"
                    temp_file.write_text(f"""export function pop{worker_id}_{i}() {{ return {i}; }}""")
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    temp_file.unlink()
            except Exception as e:
                errors.append(f"Populate {worker_id}: {str(e)}")
        
        def query_worker(worker_id: int):
            try:
                for _ in range(20):
                    search_result = self.db.search_symbol("pop")
                    query_results.append(len(search_result['functions']))
            except Exception as e:
                errors.append(f"Query worker {worker_id}: {str(e)}")
        
        try:
            populate_threads = [threading.Thread(target=populate_worker, args=(i,)) for i in range(5)]
            for t in populate_threads:
                t.start()
            for t in populate_threads:
                t.join()
            
            print(f"填充完成，开始并发查询...")
            
            query_threads = [threading.Thread(target=query_worker, args=(i,)) for i in range(10)]
            for t in query_threads:
                t.start()
            for t in query_threads:
                t.join()
            
            print(f"查询完成: {len(query_results)} 次查询")
            
            if errors:
                print(f"✗ 高负载查询测试失败，发现 {len(errors)} 个错误:")
                for err in errors[:5]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 高负载数据库查询测试通过")
                
        except Exception as e:
            print(f"✗ 高负载查询测试失败: {e}")
            success = False
        
        self.test_results['database_query_under_load'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors[:10]
        }
        return success
        
    def test_rapid_state_changes(self):
        """测试快速状态变化（文件存在->不存在->存在）"""
        print("\n" + "="*80)
        print("Test 4: 快速状态变化测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            temp_file = self.project_path / "state_test.ets"
            
            for i in range(20):
                try:
                    temp_file.write_text(f"""export function state{i}() {{ return {i}; }}""")
                    result1 = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    if result1['status'] != 'success':
                        errors.append(f"Iter {i} create: {result1['error']}")
                    
                    temp_file.unlink()
                    result2 = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    if result2['status'] != 'skipped' and result2['status'] != 'error':
                        errors.append(f"Iter {i} missing file should be skipped, got: {result2['status']}")
                    
                except Exception as e:
                    errors.append(f"Iter {i}: {str(e)}")
            
            if errors:
                print(f"✗ 快速状态变化测试失败，发现 {len(errors)} 个错误:")
                for err in errors[:5]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 快速状态变化测试通过 (20次状态切换)")
                
        except Exception as e:
            print(f"✗ 快速状态变化测试失败: {e}")
            success = False
        
        self.test_results['rapid_state_changes'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors[:10]
        }
        return success
        
    def test_very_large_batch(self):
        """测试大批量操作（500个文件）"""
        print("\n" + "="*80)
        print("Test 5: 大批量操作测试 (500个文件)")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            temp_files = []
            
            for i in range(500):
                temp_file = self.project_path / f"batch_{i}.ets"
                temp_file.write_text(f"""export function batch{i}() {{ return {i}; }}""")
                temp_files.append(temp_file)
                
                if i % 100 == 0:
                    print(f"创建文件: {i}/500")
            
            print("开始批量更新...")
            start = time.time()
            
            results = asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
            
            elapsed = time.time() - start
            print(f"批量更新完成: 成功 {results['success']}, 失败 {results['failed']}, 耗时 {elapsed:.2f}秒")
            
            if results['failed'] > 0:
                errors.extend(results['errors'][:10])
            
            for f in temp_files:
                f.unlink()
            
            db_functions = self.db.search_symbol("batch")
            function_count = len(db_functions['functions'])
            print(f"数据库中函数数量: {function_count}")
            
            if function_count < 500:
                print(f"⚠ 数据完整性问题: 预期500个函数，但只有 {function_count} 个")
                errors.append(f"Data integrity: expected 500 functions, got {function_count}")
            
            if errors:
                print(f"✗ 大批量操作测试失败，发现 {len(errors)} 个错误:")
                for err in errors[:5]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 大批量操作测试通过 (500个文件)")
                
        except Exception as e:
            print(f"✗ 大批量操作测试失败: {e}")
            success = False
        
        self.test_results['very_large_batch'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def run_all_tests(self):
        self.setup()
        
        print("🚀 开始精简版高级压力测试...")
        print(f"测试项目: {self.project_path}")
        print(f"开始时间: {datetime.now().isoformat()}")
        
        tests = [
            self.test_high_concurrency,
            self.test_binary_file_handling,
            self.test_database_query_under_load,
            self.test_rapid_state_changes,
            self.test_very_large_batch,
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
        print("📊 精简版压力测试总结")
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
    tester = FocusedStressTester("large-test-project")
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
