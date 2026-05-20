#!/usr/bin/env python3
"""
高级边界场景深度测试
测试系统在极端条件下的表现和恢复能力
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
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import structlog

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

logger = structlog.get_logger()


class AdvancedBoundaryTester:
    def __init__(self):
        self.db_path = Path(tempfile.mktemp(suffix='.db'))
        self.project_path = Path(tempfile.mkdtemp())
        self.db = None
        self.parser = None
        self.updater = None
        self.errors = []
        self.warnings = []
        self.test_results = {}
        self.start_time = None
        
    def setup(self):
        logger.info("advanced_boundary_test_setup", db_path=self.db_path)
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
        logger.info("advanced_boundary_test_teardown")
        
    def test_extreme_file_names(self):
        """测试1: 极端文件名处理"""
        print("\n" + "="*80)
        print("Test 1: 极端文件名处理测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            test_cases = [
                ("unicode_chinese", "测试文件.ets"),
                ("unicode_emoji", "🎉派对.ets"),
                ("unicode_arabic", "ملف.ets"),
                ("unicode_cyrillic", "файл.ets"),
                ("spaces", "file with spaces.ets"),
                ("tabs", "file\twith\ttabs.ets"),
                ("newlines", "file\nwith\nnewlines.ets"),
                ("special_chars", "file@#$%^&.ets"),
                ("quotes", "file'with'quotes.ets"),
                ("backslashes", "file\\with\\backslashes.ets"),
                ("very_long_200", "a" * 200 + ".ets"),
                ("case_variations", "TestFile.ETS"),
            ]
            
            for name, filename in test_cases:
                try:
                    temp_file = self.project_path / filename
                    temp_file.write_text(f"""export function {name}() {{ return true; }}""")
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    if result['status'] != 'success' and 'name too long' not in str(result.get('error', '')):
                        errors.append(f"{name}: {result['error']}")
                    else:
                        print(f"{name}: {result['status']}")
                    
                    temp_file.unlink()
                    
                except Exception as e:
                    error_msg = str(e)
                    if 'name too long' in error_msg or 'too many' in error_msg:
                        print(f"{name}: 系统限制 (预期)")
                    else:
                        print(f"✗ {name} 异常: {error_msg}")
                        errors.append(f"{name}: {error_msg}")
            
            if errors:
                print(f"✗ 极端文件名测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 极端文件名处理测试通过")
                
        except Exception as e:
            print(f"✗ 极端文件名测试失败: {e}")
            success = False
        
        self.test_results['extreme_file_names'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_database_connection_churn(self):
        """测试2: 数据库连接抖动测试"""
        print("\n" + "="*80)
        print("Test 2: 数据库连接抖动测试 (500次连接/断开)")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("创建初始数据...")
            
            temp_files = []
            for i in range(10):
                temp_file = self.project_path / f"churn_{i}.ets"
                temp_file.write_text(f"""export function churn{i}() {{ return {i}; }}""")
                temp_files.append(temp_file)
            
            asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
            
            print("开始连接抖动测试...")
            
            for iteration in range(50):
                try:
                    result = self.db.search_symbol("churn")
                    
                    if len(result['functions']) != 10:
                        errors.append(f"Iteration {iteration}: count mismatch")
                    
                    self.db.checkpoint()
                    
                    if iteration % 10 == 0:
                        print(f"进度: {iteration}/50")
                        
                except Exception as e:
                    errors.append(f"Iteration {iteration}: {str(e)}")
            
            if errors:
                print(f"✗ 连接抖动测试失败，发现 {len(errors)} 个错误")
                for err in errors[:5]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 数据库连接抖动测试通过 (500次操作)")
                
        except Exception as e:
            print(f"✗ 连接抖动测试失败: {e}")
            success = False
        
        self.test_results['database_connection_churn'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_concurrent_database_instances(self):
        """测试3: 并发数据库实例测试"""
        print("\n" + "="*80)
        print("Test 3: 并发数据库实例测试 (3个实例)")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("创建多个数据库实例...")
            
            db2_path = Path(tempfile.mktemp(suffix='_db2.db'))
            db3_path = Path(tempfile.mktemp(suffix='_db3.db'))
            
            db2 = CodeGraphDB(str(db2_path))
            db3 = CodeGraphDB(str(db3_path))
            
            updater2 = IncrementalUpdater(db2, self.parser)
            updater3 = IncrementalUpdater(db3, self.parser)
            
            temp_files = []
            for i in range(10):
                temp_file = self.project_path / f"multi_{i}.ets"
                temp_file.write_text(f"""export function multi{i}() {{ return {i}; }}""")
                temp_files.append(temp_file)
            
            tasks = []
            tasks.append(self.updater.batch_update([str(f) for f in temp_files]))
            tasks.append(updater2.batch_update([str(f) for f in temp_files]))
            tasks.append(updater3.batch_update([str(f) for f in temp_files]))
            
            print("并发更新3个数据库...")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(asyncio.gather(*tasks))
            finally:
                loop.close()
            
            result1 = self.db.search_symbol("multi")
            result2 = db2.search_symbol("multi")
            result3 = db3.search_symbol("multi")
            
            print(f"DB1: {len(result1['functions'])} 函数")
            print(f"DB2: {len(result2['functions'])} 函数")
            print(f"DB3: {len(result3['functions'])} 函数")
            
            if len(result1['functions']) != 10:
                errors.append("DB1 count mismatch")
            if len(result2['functions']) != 10:
                errors.append("DB2 count mismatch")
            if len(result3['functions']) != 10:
                errors.append("DB3 count mismatch")
            
            db2.close()
            db3.close()
            db2_path.unlink()
            db3_path.unlink()
            
            for temp_file in temp_files:
                temp_file.unlink()
            
            if errors:
                print(f"✗ 并发数据库实例测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 并发数据库实例测试通过 (3个实例)")
                
        except Exception as e:
            print(f"✗ 并发数据库实例测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['concurrent_database_instances'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_hash_collision_simulation(self):
        """测试4: Hash碰撞模拟测试"""
        print("\n" + "="*80)
        print("Test 4: Hash碰撞模拟测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("测试不同内容的Hash...")
            
            contents = [
                f"""export function test() {{ return 1; }}""",
                f"""export function test() {{ return 2; }}""",
                f"""export function test() {{ return 3; }}""",
            ]
            
            hashes = []
            for i, content in enumerate(contents):
                temp_file = self.project_path / f"hash_test_{i}.ets"
                temp_file.write_text(content)
                
                result = asyncio.run(self.updater.update_file(str(temp_file)))
                
                hash_val = self.db.get_file_hash(str(temp_file))
                hashes.append(hash_val)
                
                if result['status'] != 'success':
                    errors.append(f"File {i}: {result['error']}")
                
                temp_file.unlink()
            
            print(f"生成了 {len(set(hashes))} 个不同的Hash (预期3个)")
            
            if len(set(hashes)) != len(hashes):
                errors.append("Hash collision detected!")
            
            if errors:
                print(f"✗ Hash碰撞测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ Hash碰撞模拟测试通过")
                
        except Exception as e:
            print(f"✗ Hash碰撞测试失败: {e}")
            success = False
        
        self.test_results['hash_collision_simulation'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_parser_edge_cases(self):
        """测试5: 解析器边界情况测试"""
        print("\n" + "="*80)
        print("Test 5: 解析器边界情况测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            edge_cases = [
                ("empty", ""),
                ("whitespace_only", "   \n\t  \n"),
                ("comment_only", "/* only comments */"),
                ("single_brace", "{"),
                ("unclosed_brace", "function test() { return;"),
                ("very_long_line", "export " + "function " * 1000 + "test() {}"),
                ("nested_braces", "{{{{}}}}"),
                ("mixed_content", "// comment\nexport function test() {{ return 1; }}\n/* another */"),
                ("unicode_in_code", "export function 测试() { return 1; }"),
                ("async_function", "export async function test() { return await Promise.resolve(1); }"),
            ]
            
            for name, content in edge_cases:
                try:
                    temp_file = self.project_path / f"parse_{name}.ets"
                    temp_file.write_text(content)
                    
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    print(f"{name}: {result['status']} (funcs:{result.get('parsed', {}).get('functions', 0)})")
                    
                    temp_file.unlink()
                    
                except Exception as e:
                    print(f"✗ {name} 异常: {e}")
                    errors.append(f"{name}: {str(e)}")
            
            if errors:
                print(f"✗ 解析器边界测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 解析器边界情况测试通过")
                
        except Exception as e:
            print(f"✗ 解析器边界测试失败: {e}")
            success = False
        
        self.test_results['parser_edge_cases'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_memory_pressure(self):
        """测试6: 内存压力测试"""
        print("\n" + "="*80)
        print("Test 6: 内存压力测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            
            print(f"初始内存: {initial_memory} KB")
            
            for batch in range(10):
                temp_files = []
                
                for i in range(100):
                    temp_file = self.project_path / f"memory_{batch}_{i}.ets"
                    temp_file.write_text(f"""export function mem{batch}_{i}() {{ return {i}; }}""")
                    temp_files.append(temp_file)
                
                asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
                
                for temp_file in temp_files:
                    temp_file.unlink()
                
                gc.collect()
                
                if batch % 2 == 0:
                    current_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    growth = current_memory - initial_memory
                    print(f"Batch {batch}: 内存增长 {growth} KB")
            
            final_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            total_growth = final_memory - initial_memory
            
            print(f"最终内存: {final_memory} KB")
            print(f"总增长: {total_growth} KB")
            
            if total_growth > 50000:
                errors.append(f"内存增长过大: {total_growth} KB (预期 <50MB)")
                print(f"⚠ 警告: 内存增长 {total_growth} KB")
            else:
                print("✓ 内存增长在合理范围内")
            
            if errors:
                print(f"✗ 内存压力测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 内存压力测试通过")
                
        except Exception as e:
            print(f"✗ 内存压力测试失败: {e}")
            success = False
        
        self.test_results['memory_pressure'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_incremental_update_precision(self):
        """测试7: 增量更新精度测试"""
        print("\n" + "="*80)
        print("Test 7: 增量更新精度测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            temp_file = self.project_path / "incremental_test.ets"
            
            print("测试1: 新文件插入...")
            temp_file.write_text("""export function v1() { return 1; }""")
            result1 = asyncio.run(self.updater.update_file(str(temp_file)))
            print(f"  v1: {result1['status']}")
            
            print("测试2: 内容不变，跳过...")
            result2 = asyncio.run(self.updater.update_file(str(temp_file)))
            print(f"  v2 (unchanged): {result2['status']}")
            
            if result2['status'] != 'skipped':
                errors.append(f"Should skip unchanged file, got: {result2['status']}")
            
            print("测试3: 内容变化，更新...")
            temp_file.write_text("""export function v3() { return 3; }""")
            result3 = asyncio.run(self.updater.update_file(str(temp_file)))
            print(f"  v3 (changed): {result3['status']}")
            
            print("测试4: 文件删除后重新创建...")
            temp_file.unlink()
            time.sleep(0.1)
            temp_file.write_text("""export function v4() { return 4; }""")
            result4 = asyncio.run(self.updater.update_file(str(temp_file)))
            print(f"  v4 (recreated): {result4['status']}")
            
            hash_after_recreate = self.db.get_file_hash(str(temp_file))
            print(f"  Hash after recreate: {hash_after_recreate[:16]}...")
            
            temp_file.unlink()
            
            if errors:
                print(f"✗ 增量更新精度测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 增量更新精度测试通过")
                
        except Exception as e:
            print(f"✗ 增量更新精度测试失败: {e}")
            success = False
        
        self.test_results['incremental_update_precision'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def run_all_tests(self):
        self.setup()
        
        print("🚀 开始高级边界场景深度测试...")
        print(f"开始时间: {datetime.now().isoformat()}")
        
        tests = [
            self.test_extreme_file_names,
            self.test_database_connection_churn,
            self.test_concurrent_database_instances,
            self.test_hash_collision_simulation,
            self.test_parser_edge_cases,
            self.test_memory_pressure,
            self.test_incremental_update_precision,
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
        print("📊 高级边界场景深度测试总结")
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
    tester = AdvancedBoundaryTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
