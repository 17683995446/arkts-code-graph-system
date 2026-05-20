#!/usr/bin/env python3
"""
超高级真实场景压力测试套件
设计用于发现系统在极端条件下的潜在bug
"""
import os
import sys
import time
import random
import tempfile
import threading
import asyncio
import gc
import resource
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import structlog

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

logger = structlog.get_logger()


class ExtremeStressTester:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.db_path = Path(tempfile.mktemp(suffix='.db'))
        self.db = None
        self.parser = None
        self.updater = None
        self.errors = []
        self.warnings = []
        self.metrics = {}
        self.start_time = None
        self.test_results = {}
        
    def setup(self):
        logger.info("extreme_stress_test_setup", db_path=self.db_path)
        self.db = CodeGraphDB(str(self.db_path))
        self.parser = LocalArkTSParser()
        self.updater = IncrementalUpdater(self.db, self.parser)
        self.start_time = time.time()
        
    def teardown(self):
        if self.db:
            self.db.close()
        if self.db_path.exists():
            self.db_path.unlink()
        logger.info("extreme_stress_test_teardown")
        
    def test_massive_concurrent_writes(self):
        """测试1: 海量并发写入（100+线程同时写入）"""
        print("\n" + "="*80)
        print("Test 1: 海量并发写入测试 (100线程)")
        print("="*80)
        
        success = True
        errors = []
        files = list(self.project_path.glob("**/*.ets"))[:20]
        
        def concurrent_worker(worker_id: int, file_path: Path, iteration: int):
            try:
                content = f"""export function worker{worker_id}_iter{iteration}() {{
    return {worker_id} * {iteration};
}}"""
                temp_file = self.project_path / f"concurrent_{worker_id}_{iteration}.ets"
                temp_file.write_text(content)
                
                result = asyncio.run(self.updater.update_file(str(temp_file)))
                
                if result['status'] != 'success':
                    errors.append(f"Worker {worker_id} iteration {iteration} failed: {result['error']}")
                
                temp_file.unlink()
                
            except Exception as e:
                errors.append(f"Worker {worker_id} iteration {iteration} exception: {str(e)}")
        
        try:
            threads = []
            for i in range(100):
                file_path = files[i % len(files)]
                t = threading.Thread(target=concurrent_worker, args=(i, file_path, 1))
                threads.append(t)
                t.start()
                
                if i % 10 == 0:
                    time.sleep(0.01)
            
            for t in threads:
                t.join(timeout=30)
            
            if errors:
                print(f"✗ 海量并发写入测试失败，发现 {len(errors)} 个错误:")
                for err in errors[:5]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 海量并发写入测试通过 (100线程无错误)")
                
        except Exception as e:
            print(f"✗ 海量并发写入测试失败: {e}")
            success = False
            errors.append(str(e))
        
        self.test_results['massive_concurrent_writes'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors[:10]
        }
        return success
        
    def test_rapid_file_create_delete(self):
        """测试2: 快速文件创建和删除（模拟IDE场景）"""
        print("\n" + "="*80)
        print("Test 2: 快速文件创建和删除测试 (500次)")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            for i in range(500):
                try:
                    temp_file = self.project_path / f"rapid_{i}.ets"
                    temp_file.write_text(f"""export function func{i}() {{ return {i}; }}""")
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    if result['status'] != 'success':
                        errors.append(f"Create failed at {i}: {result['error']}")
                    
                    temp_file.unlink()
                    
                    if i % 100 == 0:
                        print(f"进度: {i}/500")
                        
                except Exception as e:
                    errors.append(f"Exception at {i}: {str(e)}")
            
            if errors:
                print(f"✗ 快速文件创建删除测试失败，发现 {len(errors)} 个错误:")
                for err in errors[:5]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 快速文件创建删除测试通过 (500次操作无错误)")
                
        except Exception as e:
            print(f"✗ 快速文件创建删除测试失败: {e}")
            success = False
        
        self.test_results['rapid_file_create_delete'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors[:10]
        }
        return success
        
    def test_database_lock_contention(self):
        """测试3: 数据库锁竞争测试（同时读写）"""
        print("\n" + "="*80)
        print("Test 3: 数据库锁竞争测试")
        print("="*80)
        
        success = True
        errors = []
        results = []
        
        def read_worker(worker_id: int):
            try:
                files = list(self.project_path.glob("**/*.ets"))[:5]
                for _ in range(20):
                    file_path = random.choice(files)
                    search_result = self.db.search_symbol("function")
                    results.append(('read', worker_id, len(search_result['functions'])))
            except Exception as e:
                errors.append(f"Read worker {worker_id}: {str(e)}")
        
        def write_worker(worker_id: int):
            try:
                for i in range(20):
                    temp_file = self.project_path / f"lock_test_{worker_id}_{i}.ets"
                    temp_file.write_text(f"""export function wf{worker_id}_{i}() {{ return {worker_id}; }}""")
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    results.append(('write', worker_id, result['status']))
                    temp_file.unlink()
            except Exception as e:
                errors.append(f"Write worker {worker_id}: {str(e)}")
        
        try:
            threads = []
            for i in range(5):
                t = threading.Thread(target=read_worker, args=(i,))
                threads.append(t)
                t.start()
                
                t = threading.Thread(target=write_worker, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join(timeout=60)
            
            if errors:
                print(f"✗ 数据库锁竞争测试失败，发现 {len(errors)} 个错误:")
                for err in errors[:5]:
                    print(f"  - {err}")
                success = False
            else:
                print(f"✓ 数据库锁竞争测试通过 ({len(results)} 操作完成)")
                
        except Exception as e:
            print(f"✗ 数据库锁竞争测试失败: {e}")
            success = False
        
        self.test_results['database_lock_contention'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors[:10]
        }
        return success
        
    def test_memory_leak_detection(self):
        """测试4: 内存泄漏检测"""
        print("\n" + "="*80)
        print("Test 4: 内存泄漏检测测试")
        print("="*80)
        
        success = True
        initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        try:
            for i in range(100):
                temp_file = self.project_path / f"memory_test_{i}.ets"
                temp_file.write_text(f"""export function mem{i}() {{ return {i}; }}""")
                
                result = asyncio.run(self.updater.update_file(str(temp_file)))
                
                if result['status'] != 'success':
                    print(f"警告: 更新失败 at {i}: {result['error']}")
                
                temp_file.unlink()
                
                if i % 20 == 0:
                    gc.collect()
                    current_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    memory_growth = current_memory - initial_memory
                    print(f"进度: {i}/100, 内存增长: {memory_growth} KB")
            
            gc.collect()
            final_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            memory_growth = final_memory - initial_memory
            
            print(f"初始内存: {initial_memory} KB")
            print(f"最终内存: {final_memory} KB")
            print(f"总内存增长: {memory_growth} KB")
            
            if memory_growth > 10000:
                print(f"⚠ 警告: 检测到可能的内存泄漏 (增长 > 10MB)")
                self.warnings.append("Possible memory leak detected")
            else:
                print("✓ 内存泄漏检测通过")
                
        except Exception as e:
            print(f"✗ 内存泄漏检测测试失败: {e}")
            success = False
        
        self.test_results['memory_leak'] = {
            'success': success,
            'initial_memory': initial_memory,
            'final_memory': final_memory,
            'growth': final_memory - initial_memory
        }
        return success
        
    def test_corrupted_data_recovery(self):
        """测试5: 数据损坏恢复测试"""
        print("\n" + "="*80)
        print("Test 5: 数据损坏恢复测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            test_cases = [
                ("empty_file", ""),
                ("binary_data", b"\x00\x01\x02\xff\xfe\xfd"),
                ("very_long_line", "a" * 100000),
                ("null_bytes", "test\x00null\x00bytes"),
                ("invalid_utf8", b"\xc0\x80\xe0\x80\xf0\x80\x80\x80"),
            ]
            
            for name, content in test_cases:
                try:
                    temp_file = self.project_path / f"corrupt_{name}.ets"
                    if isinstance(content, bytes):
                        temp_file.write_bytes(content)
                    else:
                        temp_file.write_text(content)
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    print(f"{name}: {result['status']}")
                    
                    if result['status'] == 'error':
                        print(f"  处理异常: {result['error']}")
                    else:
                        print(f"  成功处理")
                    
                    temp_file.unlink()
                    
                except Exception as e:
                    errors.append(f"{name}: {str(e)}")
                    print(f"✗ {name} 处理失败: {e}")
            
            if errors:
                print(f"\n⚠ 发现 {len(errors)} 个异常处理问题")
                success = False
            else:
                print("\n✓ 数据损坏恢复测试通过")
                
        except Exception as e:
            print(f"✗ 数据损坏恢复测试失败: {e}")
            success = False
        
        self.test_results['corrupted_data_recovery'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_edge_case_file_paths(self):
        """测试6: 边界文件路径测试"""
        print("\n" + "="*80)
        print("Test 6: 边界文件路径测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            edge_cases = [
                ("spaces in path", "test with spaces.ets"),
                ("special chars", "file-with-special!@#.ets"),
                ("unicode path", "测试文件.ets"),
                ("very_long_path", "a" * 200 + ".ets"),
                ("hidden_file", ".hidden.ets"),
                ("UPPERCASE.ETS", "UPPERCASE.ETS"),
            ]
            
            for name, filename in edge_cases:
                try:
                    temp_file = self.project_path / filename
                    temp_file.write_text(f"""export function edge_{name.replace(' ', '_')}() {{ return true; }}""")
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    print(f"{name}: {result['status']}")
                    
                    if result['status'] != 'success':
                        errors.append(f"{name}: {result['error']}")
                    
                    temp_file.unlink()
                    
                except Exception as e:
                    errors.append(f"{name}: {str(e)}")
            
            if errors:
                print(f"✗ 边界文件路径测试失败，发现 {len(errors)} 个错误:")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 边界文件路径测试通过")
                
        except Exception as e:
            print(f"✗ 边界文件路径测试失败: {e}")
            success = False
        
        self.test_results['edge_case_file_paths'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_asyncio_event_loop_stress(self):
        """测试7: 异步事件循环压力测试"""
        print("\n" + "="*80)
        print("Test 7: 异步事件循环压力测试")
        print("="*80)
        
        success = True
        errors = []
        
        async def async_worker(worker_id: int, count: int):
            for i in range(count):
                try:
                    temp_file = self.project_path / f"async_{worker_id}_{i}.ets"
                    temp_file.write_text(f"""export function aw{worker_id}_{i}() {{ return {worker_id}; }}""")
                    
                    result = await self.updater.update_file(str(temp_file))
                    
                    if result['status'] != 'success':
                        errors.append(f"Async worker {worker_id} iteration {i}: {result['error']}")
                    
                    temp_file.unlink()
                    
                except Exception as e:
                    errors.append(f"Async worker {worker_id} iteration {i}: {str(e)}")
        
        try:
            tasks = [async_worker(i, 20) for i in range(10)]
            asyncio.run(asyncio.gather(*tasks))
            
            if errors:
                print(f"✗ 异步事件循环测试失败，发现 {len(errors)} 个错误:")
                for err in errors[:5]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 异步事件循环测试通过 (200次异步操作)")
                
        except Exception as e:
            print(f"✗ 异步事件循环测试失败: {e}")
            success = False
        
        self.test_results['asyncio_stress'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors[:10]
        }
        return success
        
    def test_database_integrity_under_load(self):
        """测试8: 高负载下的数据库完整性测试"""
        print("\n" + "="*80)
        print("Test 8: 高负载下数据库完整性测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            temp_files = []
            for i in range(100):
                temp_file = self.project_path / f"integrity_{i}.ets"
                temp_file.write_text(f"""export function integ{i}() {{ return {i}; }}""")
                temp_files.append(temp_file)
            
            results = asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
            
            print(f"批量更新结果: 成功 {results['success']}, 失败 {results['failed']}, 跳过 {results['skipped']}")
            
            if results['failed'] > 0:
                errors.extend(results['errors'])
                print("失败的更新:")
                for err in results['errors'][:5]:
                    print(f"  - {err['file']}: {err['error']}")
            
            for f in temp_files:
                f.unlink()
            
            db_functions = self.db.search_symbol("integ")
            function_count = len(db_functions['functions'])
            print(f"数据库中函数数量: {function_count}")
            
            if function_count < 100:
                print(f"⚠ 警告: 预期100个函数，但数据库中只有 {function_count} 个")
                errors.append(f"Data integrity issue: expected 100 functions, found {function_count}")
            
            if errors:
                print(f"✗ 数据库完整性测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 数据库完整性测试通过")
                
        except Exception as e:
            print(f"✗ 数据库完整性测试失败: {e}")
            success = False
        
        self.test_results['database_integrity'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def run_all_tests(self):
        self.setup()
        
        print("🚀 开始超高级真实场景压力测试...")
        print(f"测试项目: {self.project_path}")
        print(f"开始时间: {datetime.now().isoformat()}")
        
        tests = [
            self.test_massive_concurrent_writes,
            self.test_rapid_file_create_delete,
            self.test_database_lock_contention,
            self.test_memory_leak_detection,
            self.test_corrupted_data_recovery,
            self.test_edge_case_file_paths,
            self.test_asyncio_event_loop_stress,
            self.test_database_integrity_under_load,
        ]
        
        for test in tests:
            test_name = test.__name__
            try:
                test()
            except Exception as e:
                print(f"✗ 测试 {test_name} 执行异常: {e}")
                self.test_results[test_name] = {
                    'success': False,
                    'error': str(e)
                }
        
        print("\n" + "="*80)
        print("📊 超高级压力测试总结")
        print("="*80)
        
        passed = sum(1 for v in self.test_results.values() if v.get('success', False))
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✓ PASSED" if result.get('success', False) else "✗ FAILED"
            errors = result.get('errors', 0)
            print(f"  {test_name}: {status} ({errors} errors)")
        
        print(f"\n总测试: {total}, 通过: {passed}, 失败: {total - passed}")
        
        if self.warnings:
            print(f"\n⚠ 发现 {len(self.warnings)} 个警告:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
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
    tester = ExtremeStressTester("large-test-project")
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
