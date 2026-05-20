#!/usr/bin/env python3
"""
完整集成测试套件
测试前后端、API、数据库的集成场景
"""
import os
import sys
import time
import json
import asyncio
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import structlog

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

logger = structlog.get_logger()


class IntegrationTester:
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
        logger.info("integration_test_setup", db_path=self.db_path)
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
        logger.info("integration_test_teardown")
        
    def test_api_search_integration(self):
        """测试1: API搜索功能集成"""
        print("\n" + "="*80)
        print("Test 1: API搜索功能集成测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            for i in range(100):
                temp_file = self.project_path / f"api_test_{i}.ets"
                temp_file.write_text(f"""export function search{i}() {{ return {i}; }}""")
                asyncio.run(self.updater.update_file(str(temp_file)))
            
            print("已插入100个文件，开始测试搜索API...")
            
            search_results = self.db.search_symbol("search")
            
            if len(search_results['functions']) != 100:
                errors.append(f"Expected 100 functions, got {len(search_results['functions'])}")
            
            print(f"搜索结果: {len(search_results['functions'])} 个函数")
            
            partial_search = self.db.search_symbol("search5")
            print(f"部分搜索 'search5': {len(partial_search['functions'])} 个函数")
            
            if len(partial_search['functions']) < 10:
                errors.append(f"Partial search failed: expected ~11, got {len(partial_search['functions'])}")
            
            for temp_file in self.project_path.glob("api_test_*.ets"):
                temp_file.unlink()
            
            if errors:
                print(f"✗ API搜索功能测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ API搜索功能测试通过")
                
        except Exception as e:
            print(f"✗ API搜索功能测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['api_search_integration'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_database_transactions(self):
        """测试2: 数据库事务完整性"""
        print("\n" + "="*80)
        print("Test 2: 数据库事务完整性测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            temp_files = []
            
            print("测试批量插入的事务完整性...")
            
            for i in range(50):
                temp_file = self.project_path / f"trans_{i}.ets"
                temp_file.write_text(f"""
export function trans{i}() {{
    return {i};
}}

export class TransClass{i} {{
    value: number = {i};
}}
""")
                temp_files.append(temp_file)
            
            results = asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
            
            print(f"批量更新结果: 成功 {results['success']}, 失败 {results['failed']}")
            
            all_funcs = self.db.search_symbol("trans")
            all_classes = self.db.search_symbol("TransClass")
            
            print(f"数据库函数数量: {len(all_funcs['functions'])}")
            print(f"数据库类数量: {len(all_classes['classes'])}")
            
            if len(all_funcs['functions']) != 50:
                errors.append(f"Function count mismatch: expected 50, got {len(all_funcs['functions'])}")
            
            if len(all_classes['classes']) != 50:
                errors.append(f"Class count mismatch: expected 50, got {len(all_classes['classes'])}")
            
            for temp_file in temp_files:
                temp_file.unlink()
            
            if errors:
                print(f"✗ 事务完整性测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 事务完整性测试通过")
                
        except Exception as e:
            print(f"✗ 事务完整性测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['database_transactions'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_concurrent_api_calls(self):
        """测试3: 并发API调用测试"""
        print("\n" + "="*80)
        print("Test 3: 并发API调用测试")
        print("="*80)
        
        success = True
        errors = []
        results = {'reads': 0, 'writes': 0, 'errors': []}
        lock = threading.Lock()
        
        def writer(worker_id: int):
            try:
                for i in range(20):
                    temp_file = self.project_path / f"concurrent_{worker_id}_{i}.ets"
                    temp_file.write_text(f"""export function concurrent{worker_id}_{i}() {{ return {worker_id}; }}""")
                    result = asyncio.run(self.updater.update_file(str(temp_file)))
                    
                    with lock:
                        results['writes'] += 1
                        if result['status'] != 'success':
                            results['errors'].append(f"Write {worker_id}_{i}: {result['error']}")
                    
                    temp_file.unlink()
            except Exception as e:
                with lock:
                    results['errors'].append(f"Writer {worker_id}: {str(e)}")
        
        def reader(worker_id: int):
            try:
                for _ in range(30):
                    search_result = self.db.search_symbol("concurrent")
                    with lock:
                        results['reads'] += 1
            except Exception as e:
                with lock:
                    results['errors'].append(f"Reader {worker_id}: {str(e)}")
        
        try:
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
            
            print(f"读取操作: {results['reads']}, 写入操作: {results['writes']}")
            print(f"错误数: {len(results['errors'])}")
            
            if results['errors']:
                errors.extend(results['errors'][:5])
                print(f"✗ 并发API调用测试失败，发现 {len(results['errors'])} 个错误")
                for err in results['errors'][:3]:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 并发API调用测试通过")
                
        except Exception as e:
            print(f"✗ 并发API调用测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['concurrent_api_calls'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_file_watcher_simulation(self):
        """测试4: 文件监控模拟测试"""
        print("\n" + "="*80)
        print("Test 4: 文件监控模拟测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("模拟IDE文件变更场景...")
            
            temp_file = self.project_path / "watcher_test.ets"
            
            for i in range(30):
                temp_file.write_text(f"""export function watcher{i}() {{ return {i}; }}""")
                result = asyncio.run(self.updater.update_file(str(temp_file)))
                
                if result['status'] != 'success':
                    errors.append(f"Iteration {i}: {result['error']}")
                
                time.sleep(0.01)
            
            hash1 = self.db.get_file_hash(str(temp_file))
            temp_file.write_text("""export function final() { return 999; }""")
            hash2 = self.db.compute_file_hash(str(temp_file))
            
            print(f"文件变更检测: hash1={hash1[:16]}..., hash2={hash2[:16]}...")
            
            if hash1 == hash2:
                errors.append("Hash should be different after content change")
            
            result = asyncio.run(self.updater.update_file(str(temp_file)))
            
            if result['status'] != 'success':
                errors.append(f"Final update failed: {result['error']}")
            
            temp_file.unlink()
            
            if errors:
                print(f"✗ 文件监控模拟测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 文件监控模拟测试通过")
                
        except Exception as e:
            print(f"✗ 文件监控模拟测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['file_watcher_simulation'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_database_backup_integrity(self):
        """测试5: 数据库备份完整性测试"""
        print("\n" + "="*80)
        print("Test 5: 数据库备份完整性测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("创建初始数据集...")
            
            temp_files = []
            for i in range(30):
                temp_file = self.project_path / f"backup_{i}.ets"
                temp_file.write_text(f"""export function backup{i}() {{ return {i}; }}""")
                temp_files.append(temp_file)
            
            asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
            
            self.db.checkpoint()
            
            import shutil
            backup_path = Path(tempfile.mktemp(suffix='_backup.db'))
            shutil.copy(self.db_path, backup_path)
            
            print("数据库已备份到新文件...")
            
            for temp_file in temp_files:
                temp_file.unlink()
            
            backup_db = CodeGraphDB(str(backup_path))
            
            search_result = backup_db.search_symbol("backup")
            print(f"从备份恢复: {len(search_result['functions'])} 个函数")
            
            if len(search_result['functions']) != 30:
                errors.append(f"Backup integrity failed: expected 30, got {len(search_result['functions'])}")
            
            backup_db.close()
            backup_path.unlink()
            
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()
            
            if errors:
                print(f"✗ 备份完整性测试失败，发现 {len(errors)} 个错误")
                success = False
            else:
                print("✓ 备份完整性测试通过")
                
        except Exception as e:
            print(f"✗ 备份完整性测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['database_backup_integrity'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_large_project_structure(self):
        """测试6: 大型项目结构测试"""
        print("\n" + "="*80)
        print("Test 6: 大型项目结构测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("创建真实项目结构...")
            
            components = self.project_path / "components"
            services = self.project_path / "services"
            utils = self.project_path / "utils"
            stores = self.project_path / "stores"
            
            components.mkdir()
            services.mkdir()
            utils.mkdir()
            stores.mkdir()
            
            files_to_create = []
            
            for i in range(20):
                comp_file = components / f"Component{i}.ets"
                comp_file.write_text(f"""
@Component
export struct Component{i} {{
    @State message: string = "Component {i}";
    
    build() {{
        Text(this.message)
    }}
}}
""")
                files_to_create.append(str(comp_file))
            
            for i in range(15):
                serv_file = services / f"Service{i}.ets"
                serv_file.write_text(f"""
export class Service{i} {{
    private data: number = {i};
    
    public getData(): number {{
        return this.data;
    }}
    
    public async fetchData(): Promise<number> {{
        return this.data;
    }}
}}
""")
                files_to_create.append(str(serv_file))
            
            for i in range(10):
                util_file = utils / f"Util{i}.ets"
                util_file.write_text(f"""
export function util{i}(param: number): number {{
    return param * {i};
}}

export const UTIL_CONSTANT{i} = {i};
""")
                files_to_create.append(str(util_file))
            
            for i in range(10):
                store_file = stores / f"Store{i}.ets"
                store_file.write_text(f"""
import {{ router }} from '@kit.ArkUI';

export class Store{i} {{
    private count: number = 0;
    
    public increment() {{
        this.count++;
    }}
    
    public getCount(): number {{
        return this.count;
    }}
}}
""")
                files_to_create.append(str(store_file))
            
            print(f"创建了 {len(files_to_create)} 个文件")
            
            results = asyncio.run(self.updater.batch_update(files_to_create))
            
            print(f"批量更新结果: 成功 {results['success']}, 失败 {results['failed']}")
            
            comp_search = self.db.search_symbol("Component")
            serv_search = self.db.search_symbol("Service")
            util_search = self.db.search_symbol("util")
            store_search = self.db.search_symbol("Store")
            
            print(f"组件数量: {len(comp_search['classes'])}")
            print(f"服务数量: {len(serv_search['classes'])}")
            print(f"工具函数数量: {len(util_search['functions'])}")
            print(f"存储类数量: {len(store_search['classes'])}")
            
            expected_counts = {
                'Component': 20,
                'Service': 15,
                'util': 10,
                'Store': 10
            }
            
            actual_counts = {
                'Component': len(comp_search['classes']),
                'Service': len(serv_search['classes']),
                'util': len(util_search['functions']),
                'Store': len(store_search['classes'])
            }
            
            for name, expected in expected_counts.items():
                actual = actual_counts[name]
                if actual != expected:
                    errors.append(f"{name} count mismatch: expected {expected}, got {actual}")
            
            import shutil
            shutil.rmtree(self.project_path)
            
            if errors:
                print(f"✗ 大型项目结构测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 大型项目结构测试通过")
                
        except Exception as e:
            print(f"✗ 大型项目结构测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['large_project_structure'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def run_all_tests(self):
        self.setup()
        
        print("🚀 开始完整集成测试...")
        print(f"开始时间: {datetime.now().isoformat()}")
        
        tests = [
            self.test_api_search_integration,
            self.test_database_transactions,
            self.test_concurrent_api_calls,
            self.test_file_watcher_simulation,
            self.test_database_backup_integrity,
            self.test_large_project_structure,
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
        print("📊 完整集成测试总结")
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
    tester = IntegrationTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
