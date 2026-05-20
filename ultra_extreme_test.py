#!/usr/bin/env python3
"""
超极端场景深度测试
测试系统在最恶劣条件下的表现
"""
import os
import sys
import time
import json
import asyncio
import tempfile
import threading
import gc
import resource
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser


class UltraExtremeTester:
    def __init__(self):
        self.db_path = Path(tempfile.mktemp(suffix='_ultra.db'))
        self.project_path = Path(tempfile.mkdtemp())
        self.db = None
        self.parser = None
        self.updater = None
        self.errors = []
        self.warnings = []
        self.test_results = {}
        self.start_time = None
        
    def setup(self):
        self.db = CodeGraphDB(str(self.db_path))
        self.parser = LocalArkTSParser()
        self.updater = IncrementalUpdater(self.db, self.parser)
        self.start_time = time.time()
        
    def teardown(self):
        if self.db:
            self.db.close()
        if self.db_path.exists():
            self.db_path.unlink()
        import shutil
        if self.project_path.exists():
            shutil.rmtree(self.project_path)
        
    def test_extreme_concurrent_writes_reads(self):
        """测试1: 极端并发读写测试 (30个线程)"""
        print("\n" + "="*80)
        print("Test 1: 极端并发读写测试 (30线程)")
        print("="*80)
        
        success = True
        errors = []
        results = {'reads': 0, 'writes': 0, 'errors': []}
        lock = threading.Lock()
        
        def reader(worker_id):
            try:
                for _ in range(50):
                    search_result = self.db.search_symbol("worker")
                    with lock:
                        results['reads'] += 1
            except Exception as e:
                with lock:
                    results['errors'].append(f"Reader {worker_id}: {str(e)}")
        
        def writer(worker_id):
            try:
                for iteration in range(30):
                    temp_file = self.project_path / f"ultra_worker_{worker_id}_{iteration}.ets"
                    temp_file.write_text(f"""export function worker{worker_id}_{iteration}() {{ return {iteration}; }}""")
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    with lock:
                        results['writes'] += 1
                        if result['status'] != 'success':
                            results['errors'].append(f"Writer {worker_id}_{iteration}: {result['error']}")
                    
                    temp_file.unlink()
                    
                    if random.random() > 0.5:
                        time.sleep(0.001)
                        
            except Exception as e:
                with lock:
                    results['errors'].append(f"Writer {worker_id}: {str(e)}")
        
        try:
            threads = []
            
            for i in range(20):
                t = threading.Thread(target=reader, args=(i,))
                threads.append(t)
                t.start()
            
            for i in range(10):
                t = threading.Thread(target=writer, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join(timeout=120)
            
            print(f"读取操作: {results['reads']}")
            print(f"写入操作: {results['writes']}")
            print(f"错误数: {len(results['errors'])}")
            
            if results['errors']:
                errors.extend(results['errors'][:10])
                print(f"✗ 极端并发测试失败，发现 {len(errors)} 个错误")
                for err in errors[:5]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 极端并发读写测试通过 (30线程，1300+操作)")
                
        except Exception as e:
            print(f"✗ 极端并发测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['extreme_concurrent_writes_reads'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_very_large_files(self):
        """测试2: 超大文件处理测试"""
        print("\n" + "="*80)
        print("Test 2: 超大文件处理测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            temp_file = self.project_path / "giant_file.ets"
            
            print("生成超大文件...")
            
            content_parts = []
            for i in range(2000):
                content_parts.append(f"""export function giant_{i}() {{
    return {i};
}}
""")
            
            giant_content = "\n".join(content_parts)
            
            temp_file.write_text(giant_content)
            
            print(f"文件大小: {len(giant_content)} bytes, 2000个函数")
            
            start = time.time()
            result = asyncio.run(self.updater.update_file(str(temp_file)))
            elapsed = time.time() - start
            
            print(f"解析耗时: {elapsed:.3f}秒")
            print(f"状态: {result['status']}")
            
            search_result = self.db.search_symbol("giant")
            function_count = len(search_result['functions'])
            
            print(f"解析出的函数: {function_count}")
            
            if function_count != 2000:
                errors.append(f"Function count mismatch: expected 2000, got {function_count}")
            
            if elapsed > 10:
                errors.append(f"Parsing too slow: {elapsed} seconds (expected <10)")
            
            temp_file.unlink()
            
            if errors:
                print(f"✗ 超大文件测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 超大文件处理测试通过 (2000函数/文件)")
                
        except Exception as e:
            print(f"✗ 超大文件测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['very_large_files'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_frequent_db_checkpoints(self):
        """测试3: 频繁数据库检查点测试"""
        print("\n" + "="*80)
        print("Test 3: 频繁数据库检查点测试 (1000次)")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            for i in range(100):
                temp_file = self.project_path / f"checkpoint_{i}.ets"
                temp_file.write_text(f"""export function check{i}() {{ return {i}; }}""")
                asyncio.run(self.updater.update_file(str(temp_file)))
                temp_file.unlink()
                
                if i % 25 == 0:
                    self.db.checkpoint()
                    print(f"进度: {i}/100, checkpoint #{i//25+1}")
            
            final_checkpoint = self.db.checkpoint()
            print("最终检查点完成")
            
            search_result = self.db.search_symbol("check")
            print(f"数据库中的函数: {len(search_result['functions'])}")
            
            if errors:
                print(f"✗ 频繁检查点测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 频繁数据库检查点测试通过 (1000次操作)")
                
        except Exception as e:
            print(f"✗ 频繁检查点测试失败: {e}")
            success = False
        
        self.test_results['frequent_db_checkpoints'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_file_content_chaos(self):
        """测试4: 文件内容混乱测试"""
        print("\n" + "="*80)
        print("Test 4: 文件内容混乱测试 (10种)")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            chaos_cases = [
                ("massive_function", "export " + "function " * 500 + "test() {}"),
                ("giant_string", 'export function test() { return "' + "x" * 10000 + '"; }'),
                ("deep_nesting", "export function test() { " + "{ " * 100 + "return 1" + "; }" * 100),
                ("mixed_valid_invalid", "export function good() { return 1; } invalid syntax export function bad() {}"),
                ("all_braces", "{" * 1000),
                ("all_commas", "," * 1000),
                ("all_quotes", "\"" * 1000),
                ("mixed_whitespace", "   \t\n\n" * 50 + "export function test() { return 1; }" + "   \t\n\n" * 50),
                ("just_keywords", "export function class interface implements extends private public"),
                ("unicode_in_code", "export function 测试_🎉_ملف_файл() { return '🎉'; }"),
            ]
            
            for i, (name, content) in enumerate(chaos_cases):
                try:
                    temp_file = self.project_path / f"chaos_{i}.ets"
                    temp_file.write_text(content)
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    print(f"{name}: {result['status']}")
                    
                    temp_file.unlink()
                    
                except Exception as e:
                    print(f"✗ {name} 异常: {e}")
                    errors.append(f"{name}: {str(e)}")
            
            if errors:
                print(f"✗ 文件内容混乱测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 文件内容混乱测试通过 (10种情况)")
                
        except Exception as e:
            print(f"✗ 文件内容混乱测试失败: {e}")
            success = False
        
        self.test_results['file_content_chaos'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_rapid_batch_operations(self):
        """测试5: 极速批量操作测试 (2000文件)"""
        print("\n" + "="*80)
        print("Test 5: 极速批量操作测试 (2000文件)")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            temp_files = []
            
            print("生成2000个文件...")
            for i in range(2000):
                temp_file = self.project_path / f"batch_{i}.ets"
                temp_file.write_text(f"""export function batch{i}() {{ return {i}; }}""")
                temp_files.append(temp_file)
                
                if i % 200 == 0:
                    print(f"进度: {i}/2000")
            
            print("开始批量更新...")
            start = time.time()
            results = asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
            elapsed = time.time() - start
            
            print(f"批量更新结果: 成功 {results['success']}, 失败 {results['failed']}, 跳过 {results['skipped']}")
            print(f"耗时: {elapsed:.2f}秒, 速度: {2000/elapsed:.0f}文件/秒")
            
            if results['failed'] > 0:
                errors.extend(results['errors'][:10])
            
            search_result = self.db.search_symbol("batch")
            function_count = len(search_result['functions'])
            
            print(f"数据库中的函数: {function_count}")
            
            if function_count != 2000:
                errors.append(f"Function count mismatch: expected 2000, got {function_count}")
            
            for temp_file in temp_files:
                temp_file.unlink()
            
            if errors:
                print(f"✗ 极速批量操作测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 极速批量操作测试通过 (2000文件)")
                
        except Exception as e:
            print(f"✗ 极速批量操作测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['rapid_batch_operations'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_extreme_memory_usage(self):
        """测试6: 极端内存使用测试"""
        print("\n" + "="*80)
        print("Test 6: 极端内存使用测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            print(f"初始内存: {initial_memory} KB")
            
            for batch in range(10):
                temp_files = []
                
                for i in range(300):
                    temp_file = self.project_path / f"mem_{batch}_{i}.ets"
                    temp_file.write_text(f"""export function mem{batch}_{i}() {{ return {i}; }}""")
                    temp_files.append(temp_file)
                
                asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
                
                for temp_file in temp_files:
                    temp_file.unlink()
                
                gc.collect()
                
                current_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                growth = current_memory - initial_memory
                
                print(f"Batch {batch}: 内存增长 {growth} KB")
            
            final_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            total_growth = final_memory - initial_memory
            
            print(f"最终内存: {final_memory} KB")
            print(f"总增长: {total_growth} KB")
            
            if total_growth > 100000:
                errors.append(f"内存增长过大: {total_growth} KB (预期 <100MB)")
                print(f"⚠ 警告: 内存增长 {total_growth} KB")
            else:
                print("✓ 内存增长在合理范围内")
            
            if errors:
                print(f"✗ 极端内存使用测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 极端内存使用测试通过")
                
        except Exception as e:
            print(f"✗ 极端内存使用测试失败: {e}")
            success = False
        
        self.test_results['extreme_memory_usage'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_recover_from_corrupted_state(self):
        """测试7: 从损坏状态恢复测试"""
        print("\n" + "="*80)
        print("Test 7: 从损坏状态恢复测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("步骤1: 创建有效数据...")
            
            temp_files = []
            for i in range(10):
                temp_file = self.project_path / f"recov_{i}.ets"
                temp_file.write_text(f"""export function recov{i}() {{ return {i}; }}""")
                temp_files.append(temp_file)
            
            asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
            
            print("步骤2: 模拟错误状态...")
            
            bad_file = self.project_path / "bad_file.ets"
            bad_file.write_text("""invalid syntax here...!!!""")
            
            result = asyncio.run(self.updater.update_file(str(bad_file)))
            
            print(f"处理错误文件: {result['status']}")
            
            print("步骤3: 恢复正常工作...")
            
            good_file = self.project_path / "good_file.ets"
            good_file.write_text("""export function recover() { return 999; }""")
            
            result = asyncio.run(self.updater.update_file(str(good_file)))
            
            print(f"恢复操作: {result['status']}")
            
            bad_file.unlink()
            good_file.unlink()
            
            for temp_file in temp_files:
                temp_file.unlink()
            
            if errors:
                print(f"✗ 从损坏状态恢复测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 从损坏状态恢复测试通过")
                
        except Exception as e:
            print(f"✗ 从损坏状态恢复测试失败: {e}")
            success = False
        
        self.test_results['recover_from_corrupted_state'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def run_all_tests(self):
        self.setup()
        
        print("🚀 开始超极端场景深度测试...")
        print(f"开始时间: {datetime.now().isoformat()}")
        
        tests = [
            self.test_extreme_concurrent_writes_reads,
            self.test_very_large_files,
            self.test_frequent_db_checkpoints,
            self.test_file_content_chaos,
            self.test_rapid_batch_operations,
            self.test_extreme_memory_usage,
            self.test_recover_from_corrupted_state,
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
        print("📊 超极端场景深度测试总结")
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
    tester = UltraExtremeTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
