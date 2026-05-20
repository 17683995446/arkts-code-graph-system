#!/usr/bin/env python3
"""
后端API和性能深度测试
专注测试API端点和极端性能场景
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
import structlog

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

logger = structlog.get_logger()


class BackendAPITester:
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
        logger.info("backend_api_test_setup", db_path=self.db_path)
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
        logger.info("backend_api_test_teardown")
        
    def test_complex_search_queries(self):
        """测试1: 复杂搜索查询"""
        print("\n" + "="*80)
        print("Test 1: 复杂搜索查询测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            test_data = [
                ("UserService", "service"),
                ("ProductController", "controller"),
                ("getUserById", "get"),
                ("setProductName", "set"),
                ("handleOrderCreate", "handle"),
                ("calculateTotal", "calculate"),
                ("validateInput", "validate"),
            ]
            
            for i, (name, keyword) in enumerate(test_data):
                for j in range(10):
                    temp_file = self.project_path / f"complex_{i}_{j}.ets"
                    temp_file.write_text(f"""
export function {name.lower()}_{j}() {{
    return {j};
}}

export class {name} {{
    private data: number = {j};
    
    public {keyword}_{j}(): number {{
        return this.data;
    }}
}}
""")
                    asyncio.run(self.updater.update_file(str(temp_file)))
            
            print("已插入70个文件，开始复杂搜索测试...")
            
            search_tests = [
                ("UserService", 10),
                ("Service", 20),
                ("get", 10),
                ("Set", 10),
            ]
            
            for search_term, expected_min in search_tests:
                result = self.db.search_symbol(search_term)
                total = (len(result['functions']) + len(result['classes']))
                print(f"搜索 '{search_term}': {total} 个结果")
                
                if total < expected_min:
                    errors.append(f"Search '{search_term}': expected >={expected_min}, got {total}")
            
            for temp_file in self.project_path.glob("complex_*.ets"):
                temp_file.unlink()
            
            if errors:
                print(f"✗ 复杂搜索查询测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 复杂搜索查询测试通过")
                
        except Exception as e:
            print(f"✗ 复杂搜索查询测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['complex_search_queries'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_rapid_api_calls(self):
        """测试2: 极速API调用"""
        print("\n" + "="*80)
        print("Test 2: 极速API调用测试 (1000+ ops)")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("创建测试数据...")
            
            temp_files = []
            for i in range(100):
                temp_file = self.project_path / f"rapid_api_{i}.ets"
                temp_file.write_text(f"""export function rapid{i}() {{ return {i}; }}""")
                temp_files.append(temp_file)
            
            asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
            
            print(f"开始极速API调用测试...")
            
            start = time.time()
            api_calls = 0
            
            for _ in range(1000):
                search_result = self.db.search_symbol("rapid")
                api_calls += 1
                
                if api_calls % 200 == 0:
                    elapsed = time.time() - start
                    rate = api_calls / elapsed
                    print(f"进度: {api_calls}/1000, 速度: {rate:.2f} ops/sec")
            
            elapsed = time.time() - start
            rate = api_calls / elapsed
            
            print(f"完成: {api_calls} 次API调用")
            print(f"总耗时: {elapsed:.2f}秒")
            print(f"平均速度: {rate:.2f} ops/sec")
            
            if rate < 500:
                errors.append(f"API速度过慢: {rate:.2f} ops/sec (预期 >500)")
            
            for temp_file in temp_files:
                temp_file.unlink()
            
            if errors:
                print(f"✗ 极速API调用测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 极速API调用测试通过")
                
        except Exception as e:
            print(f"✗ 极速API调用测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['rapid_api_calls'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_database_growth(self):
        """测试3: 数据库增长测试"""
        print("\n" + "="*80)
        print("Test 3: 数据库增长测试")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            initial_size = self.db_path.stat().st_size
            print(f"初始数据库大小: {initial_size} bytes")
            
            print("插入1000个文件...")
            
            temp_files = []
            for i in range(1000):
                temp_file = self.project_path / f"growth_{i}.ets"
                temp_file.write_text(f"""
export function growth{i}() {{ return {i}; }}

export class Growth{i} {{
    value: number = {i};
    
    public method{i}(): number {{
        return this.value;
    }}
}}
""")
                temp_files.append(temp_file)
                
                if i % 100 == 0:
                    asyncio.run(self.updater.update_file(str(temp_file)))
                    current_size = self.db_path.stat().st_size
                    growth = current_size - initial_size
                    print(f"进度: {i}/1000, 增长: {growth} bytes")
            
            asyncio.run(self.updater.batch_update([str(f) for f in temp_files[900:]]))
            
            final_size = self.db_path.stat().st_size
            growth = final_size - initial_size
            
            print(f"最终数据库大小: {final_size} bytes")
            print(f"总增长: {growth} bytes")
            print(f"平均每个文件: {growth/1000:.2f} bytes")
            
            if growth > 10 * 1024 * 1024:
                errors.append(f"数据库增长过大: {growth} bytes (预期 <10MB)")
            
            for temp_file in temp_files:
                temp_file.unlink()
            
            if errors:
                print(f"✗ 数据库增长测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 数据库增长测试通过")
                
        except Exception as e:
            print(f"✗ 数据库增长测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['database_growth'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_concurrent_read_heavy(self):
        """测试4: 读密集型并发测试"""
        print("\n" + "="*80)
        print("Test 4: 读密集型并发测试 (20读线程)")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("创建测试数据...")
            
            temp_files = []
            for i in range(50):
                temp_file = self.project_path / f"read_heavy_{i}.ets"
                temp_file.write_text(f"""export function readHeavy{i}() {{ return {i}; }}""")
                temp_files.append(temp_file)
            
            asyncio.run(self.updater.batch_update([str(f) for f in temp_files]))
            
            results = {'reads': 0, 'errors': []}
            lock = threading.Lock()
            
            def reader_worker(worker_id: int):
                try:
                    for _ in range(200):
                        search_result = self.db.search_symbol("readHeavy")
                        
                        with lock:
                            results['reads'] += 1
                            
                        if len(search_result['functions']) != 50:
                            with lock:
                                results['errors'].append(f"Worker {worker_id}: inconsistent count")
                except Exception as e:
                    with lock:
                        results['errors'].append(f"Worker {worker_id}: {str(e)}")
            
            threads = []
            start = time.time()
            
            for i in range(20):
                t = threading.Thread(target=reader_worker, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join(timeout=60)
            
            elapsed = time.time() - start
            rate = results['reads'] / elapsed
            
            print(f"读取操作: {results['reads']}")
            print(f"耗时: {elapsed:.2f}秒")
            print(f"速度: {rate:.2f} reads/sec")
            print(f"错误数: {len(results['errors'])}")
            
            if results['errors']:
                errors.extend(results['errors'][:5])
            
            if rate < 1000:
                errors.append(f"读速度过慢: {rate:.2f} reads/sec (预期 >1000)")
            
            for temp_file in temp_files:
                temp_file.unlink()
            
            if errors:
                print(f"✗ 读密集型并发测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 读密集型并发测试通过")
                
        except Exception as e:
            print(f"✗ 读密集型并发测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['concurrent_read_heavy'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def test_mixed_workload(self):
        """测试5: 混合工作负载测试"""
        print("\n" + "="*80)
        print("Test 5: 混合工作负载测试 (读写混合)")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            results = {'reads': 0, 'writes': 0, 'errors': []}
            lock = threading.Lock()
            
            def mixed_worker(worker_id: int):
                try:
                    for i in range(30):
                        if i % 3 == 0:
                            temp_file = self.project_path / f"mixed_{worker_id}_{i}.ets"
                            temp_file.write_text(f"""export function mixed{worker_id}_{i}() {{ return {i}; }}""")
                            result = asyncio.run(self.updater.update_file(str(temp_file)))
                            
                            with lock:
                                results['writes'] += 1
                                if result['status'] != 'success':
                                    results['errors'].append(f"Write {worker_id}_{i}: {result['status']}")
                            
                            temp_file.unlink()
                        else:
                            search_result = self.db.search_symbol("mixed")
                            
                            with lock:
                                results['reads'] += 1
                                
                except Exception as e:
                    with lock:
                        results['errors'].append(f"Worker {worker_id}: {str(e)}")
            
            threads = []
            start = time.time()
            
            for i in range(20):
                t = threading.Thread(target=mixed_worker, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join(timeout=60)
            
            elapsed = time.time() - start
            total_ops = results['reads'] + results['writes']
            rate = total_ops / elapsed
            
            print(f"读取操作: {results['reads']}")
            print(f"写入操作: {results['writes']}")
            print(f"总操作: {total_ops}")
            print(f"耗时: {elapsed:.2f}秒")
            print(f"速度: {rate:.2f} ops/sec")
            print(f"错误数: {len(results['errors'])}")
            
            if results['errors']:
                errors.extend(results['errors'][:5])
            
            if rate < 100:
                errors.append(f"混合工作负载速度过慢: {rate:.2f} ops/sec (预期 >100)")
            
            if errors:
                print(f"✗ 混合工作负载测试失败，发现 {len(errors)} 个错误")
                for err in errors:
                    print(f"  - {err}")
                success = False
            else:
                print("✓ 混合工作负载测试通过")
                
        except Exception as e:
            print(f"✗ 混合工作负载测试失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['mixed_workload'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
        
    def run_all_tests(self):
        self.setup()
        
        print("🚀 开始后端API和性能深度测试...")
        print(f"开始时间: {datetime.now().isoformat()}")
        
        tests = [
            self.test_complex_search_queries,
            self.test_rapid_api_calls,
            self.test_database_growth,
            self.test_concurrent_read_heavy,
            self.test_mixed_workload,
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
        print("📊 后端API和性能深度测试总结")
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
    tester = BackendAPITester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
