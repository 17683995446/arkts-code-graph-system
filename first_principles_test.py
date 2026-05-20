#!/usr/bin/env python3
"""
第一性原理深度测试
从系统核心组件的本质出发，测试其极限能力和边界情况
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


class FirstPrinciplesTester:
    def __init__(self):
        self.db_path = Path(tempfile.mktemp(suffix='_fp.db'))
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
    
    def test_regex_boundary_cases(self):
        """第一性测试1: 正则表达式的边界情况
        
        核心问题: 正则表达式是否能在所有边界情况下正确匹配？
        """
        print("\n" + "="*80)
        print("第一性测试1: 正则表达式边界情况")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            test_cases = [
                ("empty_params", "export function test() {}"),
                ("no_params", "export function test() {}"),
                ("multi_params", "export function test(a: string, b: number, c: boolean) {}"),
                ("return_type", "export function test(): number {}"),
                ("async_func", "export async function test(): Promise<void> {}"),
                ("generator", "export function* test() {}"),
                ("no_export", "function test() {}"),
                ("deep_nesting", "export function test() { function inner() { function deeper() {} } }"),
                ("comment_in_params", "export function test(a /* comment */, b) {}"),
                ("newline_in_body", "export function test()\n{\nreturn 1;\n}"),
                ("chinese_in_code", "export function 测试函数(): number { return 1; }"),
                ("emoji_in_name", "export function 🎉() {}"),
                ("underscore_name", "export function __test__() {}"),
                ("number_start", "export function test1() {}"),
                ("mixed_case", "export function TestMixedCASE() {}"),
            ]
            
            for name, code in test_cases:
                try:
                    result = self.parser.parse_content(code, name)
                    
                    print(f"{name}: {len(result.functions)} 函数, {len(result.classes)} 类")
                    
                    if name not in ["empty_params", "no_export"] and len(result.functions) == 0:
                        errors.append(f"{name}: 预期至少1个函数，实际 {len(result.functions)}")
                    
                except Exception as e:
                    errors.append(f"{name}: {str(e)}")
                    print(f"✗ {name} 异常: {e}")
            
            if errors:
                print(f"✗ 正则表达式边界测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 正则表达式边界测试通过")
                
        except Exception as e:
            print(f"✗ 正则表达式边界测试失败: {e}")
            success = False
        
        self.test_results['regex_boundary_cases'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_database_acid_properties(self):
        """第一性测试2: 数据库ACID特性
        
        核心问题: 数据库的事务是否满足ACID特性？
        """
        print("\n" + "="*80)
        print("第一性测试2: 数据库ACID特性")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("测试A (原子性)...")
            
            temp_file = self.project_path / "acid_test.ets"
            temp_file.write_text("""export function atomic() { return 1; }
export class AtomicClass { value = 1; }""")
            
            result = asyncio.run(self.updater.update_file(str(temp_file)))
            
            if result['status'] != 'success':
                errors.append(f"原子性测试失败: {result['error']}")
            
            search = self.db.search_symbol("atomic")
            func_count = len(search['functions'])
            class_count = len(search['classes'])
            
            print(f"原子性: {func_count} 函数, {class_count} 类")
            
            if func_count == 0 or class_count == 0:
                errors.append("原子性失败: 预期1函数+1类")
            
            print("测试C (一致性)...")
            
            before_search = self.db.search_symbol("atomic")
            before_count = len(before_search['functions'])
            
            temp_file.write_text("""export function atomic() { return 2; }""")
            result2 = asyncio.run(self.updater.update_file(str(temp_file)))
            
            after_search = self.db.search_symbol("atomic")
            after_count = len(after_search['functions'])
            
            print(f"一致性: 更新前 {before_count}, 更新后 {after_count}")
            
            if before_count != after_count:
                errors.append("一致性失败: 更新后函数数量变化")
            
            print("测试I (隔离性)...")
            
            results = []
            def reader(rid):
                for _ in range(50):
                    r = self.db.search_symbol("atomic")
                    results.append(len(r['functions']))
            
            threads = []
            for i in range(10):
                t = threading.Thread(target=reader, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            isolation_violations = [r for r in results if r != 1]
            print(f"隔离性: 总读取 {len(results)}, 违规 {len(isolation_violations)}")
            
            if len(isolation_violations) > 0:
                errors.append(f"隔离性违规: {len(isolation_violations)} 次")
            
            print("测试D (持久性)...")
            
            self.db.checkpoint()
            
            search_after_checkpoint = self.db.search_symbol("atomic")
            
            print(f"持久性: checkpoint后 {len(search_after_checkpoint['functions'])} 函数")
            
            if len(search_after_checkpoint['functions']) != 1:
                errors.append("持久性失败: checkpoint后数据丢失")
            
            temp_file.unlink()
            
            if errors:
                print(f"✗ ACID测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ ACID特性测试通过")
                
        except Exception as e:
            print(f"✗ ACID测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['database_acid_properties'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_incremental_hash_collision(self):
        """第一性测试3: 增量更新Hash碰撞
        
        核心问题: 系统如何处理Hash碰撞？是否会导致数据丢失？
        """
        print("\n" + "="*80)
        print("第一性测试3: 增量更新Hash碰撞")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("测试1: 不同内容但可能碰撞的Hash...")
            
            contents = [
                "export function test() { return 1; }",
                "export function test() { return 2; }",
                "export function test() { return '1'; }",
            ]
            
            hashes = []
            for i, content in enumerate(contents):
                temp_file = self.project_path / f"hash_collision_{i}.ets"
                temp_file.write_text(content)
                
                result = asyncio.run(self.updater.update_file(str(temp_file)))
                
                if result['status'] != 'success':
                    errors.append(f"文件 {i} 更新失败: {result['error']}")
                
                hash_val = self.db.compute_file_hash(str(temp_file))
                hashes.append(hash_val)
                
                temp_file.unlink()
            
            print(f"3个不同内容产生 {len(set(hashes))} 个不同的Hash")
            
            if len(set(hashes)) != len(hashes):
                errors.append(f"Hash碰撞检测: {len(hashes)}个内容但只有{len(set(hashes))}个唯一Hash")
            
            print("测试2: Hash变化的正确检测...")
            
            temp_file = self.project_path / "hash_change.ets"
            temp_file.write_text("export function v1() { return 1; }")
            
            result1 = asyncio.run(self.updater.update_file(str(temp_file)))
            hash1 = self.db.get_file_hash(str(temp_file))
            
            temp_file.write_text("export function v2() { return 2; }")
            result2 = asyncio.run(self.updater.update_file(str(temp_file)))
            hash2 = self.db.get_file_hash(str(temp_file))
            
            print(f"Hash变化: {hash1[:16]}... -> {hash2[:16]}...")
            
            if hash1 == hash2:
                errors.append("Hash未变化，但内容已修改")
            
            temp_file.unlink()
            
            if errors:
                print(f"✗ Hash碰撞测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ Hash碰撞测试通过")
                
        except Exception as e:
            print(f"✗ Hash碰撞测试失败: {e}")
            success = False
        
        self.test_results['incremental_hash_collision'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_component_integration_accuracy(self):
        """第一性测试4: 组件集成准确性
        
        核心问题: 解析器、数据库、增量更新器三个组件的集成是否准确？
        """
        print("\n" + "="*80)
        print("第一性测试4: 组件集成准确性")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("场景1: 完整流程测试...")
            
            temp_file = self.project_path / "integration.ets"
            temp_file.write_text("""
export function getUser(id: number): User {
    return { id, name: "test" };
}

export class UserService {
    private users: Map<number, User>;
    
    constructor() {
        this.users = new Map();
    }
    
    public findUser(id: number): User | null {
        return this.users.get(id) || null;
    }
}

export interface User {
    id: number;
    name: string;
}
""")
            
            result = asyncio.run(self.updater.update_file(str(temp_file)))
            
            if result['status'] != 'success':
                errors.append(f"集成更新失败: {result['error']}")
            
            parsed = result.get('parsed', {})
            print(f"解析结果: {parsed}")
            
            if parsed.get('functions', 0) != 2:
                errors.append(f"函数数量错误: 预期2 (getUser+findUser)，实际 {parsed.get('functions', 0)}")
            
            if parsed.get('classes', 0) != 1:
                errors.append(f"类数量错误: 预期1，实际 {parsed.get('classes', 0)}")
            
            if parsed.get('interfaces', 0) != 1:
                errors.append(f"接口数量错误: 预期1，实际 {parsed.get('interfaces', 0)}")
            
            print("场景2: 数据持久化测试...")
            
            search = self.db.search_symbol("User")
            print(f"搜索'User': {len(search['functions'])} 函数, {len(search['classes'])} 类, {len(search['interfaces'])} 接口")
            
            if len(search['functions']) < 2:
                errors.append(f"持久化失败: 预期至少2个函数，实际 {len(search['functions'])}")
            
            if len(search['classes']) < 1:
                errors.append(f"持久化失败: 预期1个类，实际 {len(search['classes'])}")
            
            print("场景3: 多次更新一致性...")
            
            for i in range(5):
                temp_file.write_text(f"export function update{i}() {{ return {i}; }}")
                result = asyncio.run(self.updater.update_file(str(temp_file)))
                
                if result['status'] != 'success':
                    errors.append(f"第{i+1}次更新失败")
            
            final_search = self.db.search_symbol("update")
            print(f"5次更新后: {len(final_search['functions'])} 个函数")
            
            if len(final_search['functions']) != 1:
                errors.append(f"多次更新一致性失败: 预期1，实际 {len(final_search['functions'])} (同一文件应保留最后版本)")
            
            temp_file.unlink()
            
            if errors:
                print(f"✗ 组件集成测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 组件集成准确性测试通过")
                
        except Exception as e:
            print(f"✗ 组件集成测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['component_integration_accuracy'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_concurrent_consistency(self):
        """第一性测试5: 并发一致性
        
        核心问题: 在并发环境下，系统是否保持数据一致性？
        """
        print("\n" + "="*80)
        print("第一性测试5: 并发一致性")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("创建初始数据集...")
            
            temp_files = []
            for i in range(10):
                temp_file = self.project_path / f"concurrent_{i}.ets"
                temp_file.write_text(f"""export function func{i}() {{ return {i}; }}""")
                temp_files.append(temp_file)
            
            asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
            
            print("开始并发读写测试...")
            
            results = {
                'writes': [],
                'reads': [],
                'errors': []
            }
            lock = threading.Lock()
            
            def writer(worker_id):
                try:
                    for i in range(10):
                        temp_file = self.project_path / f"writer_{worker_id}_{i}.ets"
                        temp_file.write_text(f"""export function writer{worker_id}() {{ return {i}; }}""")
                        
                        result = asyncio.run(self.updater.update_file(str(temp_file)))
                        
                        with lock:
                            results['writes'].append(result['status'])
                            if result['status'] != 'success':
                                results['errors'].append(f"Writer {worker_id}: {result['error']}")
                        
                except Exception as e:
                    with lock:
                        results['errors'].append(f"Writer {worker_id}: {str(e)}")
            
            def reader(worker_id):
                try:
                    for _ in range(20):
                        search = self.db.search_symbol("concurrent")
                        
                        with lock:
                            results['reads'].append(len(search['functions']))
                            
                except Exception as e:
                    with lock:
                        results['errors'].append(f"Reader {worker_id}: {str(e)}")
            
            threads = []
            
            for i in range(5):
                t = threading.Thread(target=writer, args=(i,))
                threads.append(t)
                t.start()
            
            for i in range(10):
                t = threading.Thread(target=reader, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join(timeout=60)
            
            print("清理临时文件...")
            for i in range(5):
                for j in range(10):
                    temp_file = self.project_path / f"writer_{i}_{j}.ets"
                    if temp_file.exists():
                        temp_file.unlink()
            
            write_success = results['writes'].count('success')
            write_total = len(results['writes'])
            
            print(f"写入: {write_success}/{write_total} 成功")
            print(f"读取: {len(results['reads'])} 次")
            print(f"错误: {len(results['errors'])} 个")
            
            if write_success < write_total * 0.9:
                errors.append(f"写入成功率过低: {write_success}/{write_total}")
            
            if len(results['errors']) > 0:
                errors.extend(results['errors'][:5])
            
            print("验证最终数据一致性...")
            
            final_search = self.db.search_symbol("writer")
            final_count = len(final_search['functions'])
            
            print(f"最终数据库: {final_count} 个函数")
            
            if final_count != 50:
                errors.append(f"并发写入数据不一致: 预期50（5个worker各写10次同名函数），实际 {final_count}")
            
            if errors:
                print(f"✗ 并发一致性测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 并发一致性测试通过")
                
        except Exception as e:
            print(f"✗ 并发一致性测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['concurrent_consistency'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_error_recovery_completeness(self):
        """第一性测试6: 错误恢复完整性
        
        核心问题: 系统在遇到错误后，能否完整恢复并继续工作？
        """
        print("\n" + "="*80)
        print("第一性测试6: 错误恢复完整性")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("场景1: 处理无效语法...")
            
            bad_file = self.project_path / "bad_syntax.ets"
            bad_file.write_text("this is not valid syntax at all !!!")
            
            result = asyncio.run(self.updater.update_file(str(bad_file)))
            
            print(f"无效语法处理: {result['status']}")
            
            print("场景2: 从错误中恢复...")
            
            good_file = self.project_path / "good_syntax.ets"
            good_file.write_text("export function recovery() { return 42; }")
            
            result2 = asyncio.run(self.updater.update_file(str(good_file)))
            
            print(f"恢复操作: {result2['status']}")
            
            if result2['status'] != 'success':
                errors.append(f"从错误恢复失败: {result2['error']}")
            
            search = self.db.search_symbol("recovery")
            
            if len(search['functions']) != 1:
                errors.append(f"恢复后数据缺失: 预期1个函数，实际 {len(search['functions'])}")
            
            print("场景3: 混合有效和无效文件...")
            
            mixed_files = []
            for i in range(10):
                temp_file = self.project_path / f"mixed_{i}.ets"
                if i % 3 == 0:
                    temp_file.write_text(f"export function mixed{i}() {{ return {i}; }}")
                else:
                    temp_file.write_text("invalid syntax here")
                mixed_files.append(str(temp_file))
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                batch_results = loop.run_until_complete(self.updater.batch_update(mixed_files))
            finally:
                loop.close()
            
            print(f"混合文件处理: 成功 {batch_results['success']}, 失败 {batch_results['failed']}")
            
            if batch_results['failed'] > 0 and batch_results['failed'] < 7:
                errors.append(f"混合文件处理异常: {batch_results['failed']} 个失败")
            
            bad_file.unlink()
            good_file.unlink()
            
            for temp_file in mixed_files:
                Path(temp_file).unlink()
            
            if errors:
                print(f"✗ 错误恢复测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 错误恢复完整性测试通过")
                
        except Exception as e:
            print(f"✗ 错误恢复测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['error_recovery_completeness'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_long_running_stability(self):
        """第一性测试7: 长时间运行稳定性
        
        核心问题: 系统在长时间运行中是否保持稳定？
        """
        print("\n" + "="*80)
        print("第一性测试7: 长时间运行稳定性 (模拟)")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            print(f"初始内存: {initial_memory} KB")
            
            print("模拟100轮快速迭代...")
            
            for round_num in range(100):
                temp_files = []
                
                for i in range(20):
                    temp_file = self.project_path / f"round_{round_num}_{i}.ets"
                    temp_file.write_text(f"""export function round{round_num}_{i}() {{ return {i}; }}""")
                    temp_files.append(temp_file)
                
                asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
                
                for temp_file in temp_files:
                    temp_file.unlink()
                
                if round_num % 20 == 0:
                    gc.collect()
                    current_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    memory_growth = current_memory - initial_memory
                    print(f"Round {round_num}: 内存增长 {memory_growth} KB")
            
            final_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            total_growth = final_memory - initial_memory
            
            print(f"最终内存: {final_memory} KB")
            print(f"总内存增长: {total_growth} KB")
            
            if total_growth > 50000:
                errors.append(f"内存增长过大: {total_growth} KB (预期 <50MB)")
            
            print("验证数据库仍然正常工作...")
            
            test_file = self.project_path / "stability_test.ets"
            test_file.write_text("export function stability() { return 999; }")
            
            result = asyncio.run(self.updater.update_file(str(test_file)))
            
            if result['status'] != 'success':
                errors.append(f"长时间运行后功能异常: {result['error']}")
            
            search = self.db.search_symbol("stability")
            
            if len(search['functions']) != 1:
                errors.append(f"长时间运行后数据异常: {len(search['functions'])} 个函数")
            
            test_file.unlink()
            
            if errors:
                print(f"✗ 长时间运行稳定性测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 长时间运行稳定性测试通过")
                
        except Exception as e:
            print(f"✗ 长时间运行稳定性测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['long_running_stability'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def run_all_tests(self):
        self.setup()
        
        print("🚀 开始第一性原理深度测试...")
        print(f"开始时间: {datetime.now().isoformat()}")
        
        tests = [
            self.test_regex_boundary_cases,
            self.test_database_acid_properties,
            self.test_incremental_hash_collision,
            self.test_component_integration_accuracy,
            self.test_concurrent_consistency,
            self.test_error_recovery_completeness,
            self.test_long_running_stability,
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
        
        self.teardown()
        
        print("\n" + "="*80)
        print("📊 第一性原理深度测试总结")
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
    tester = FirstPrinciplesTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
