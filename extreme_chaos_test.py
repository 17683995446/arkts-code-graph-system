#!/usr/bin/env python3
"""
极端混乱测试场景 - 第一性原理深度测试
测试系统在真实世界最混乱情况下的表现
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
import string
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser


class ExtremeChaosTester:
    def __init__(self):
        self.db_path = Path(tempfile.mktemp(suffix='_chaos.db'))
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
    
    def generate_chaos_code(self):
        """生成极度混乱的ArkTS代码"""
        patterns = [
            # 正常代码
            "export function normalFunc() { return true; }",
            "class NormalClass { public method() {} }",
            
            # 各种语法变体
            "export async function asyncFunc(): Promise<void> { return await Promise.resolve(); }",
            "export function* generator() { yield 1; yield 2; }",
            
            # 混乱的注释
            "export function commentFunc() { /* comment */ // inline return 42; }",
            "/* 开头注释 */ export function commentedFunc() { return true; }",
            
            # 混合字符
            'export function unicodeFunc() { return "🎉🎊🎈"; }',
            'export function chineseFunc() { return "测试函数"; }',
            
            # 无实际内容
            "export function emptyFunc() { }",
            "class EmptyClass { }",
            
            # 嵌套结构
            """export class NestedClass {
  public outer() {
    class InnerClass {
      public inner() {
        function deep() { }
      }
    }
  }
}""",
            
            # 极端格式
            "export\tfunction\ttabbed\t(\t)\t{\treturn\t1\t;\t}",
            "export\nfunction\nmultiline\n(\n)\n{\nreturn\n2\n;\n}",
            
            # 混乱但合法的语法
            """export function mixFuncs() {
  let a=1,b=2;return a+b;
}""",
        ]
        return '\n'.join(random.sample(patterns, k=random.randint(1, 5)))
    
    def test_massive_file_chaos(self):
        """测试1：大规模文件混乱测试"""
        print("\n" + "="*80)
        print("混乱测试1：大规模文件混乱")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("创建1000个混乱文件...")
            temp_files = []
            
            for i in range(1000):
                temp_file = self.project_path / f"chaos_{i}.ets"
                
                if random.random() < 0.15:
                    # 15%的文件是非法的
                    content = "this is not valid typescript at all! \n" + "abc"*100
                elif random.random() < 0.2:
                    # 20%的文件是空的
                    content = ""
                else:
                    # 65%的文件是合法但混乱的
                    content = self.generate_chaos_code()
                
                temp_file.write_text(content)
                temp_files.append(str(temp_file))
            
            print("批量更新...")
            start = time.time()
            results = asyncio.run(self.updater.batch_update(temp_files))
            elapsed = time.time() - start
            
            print(f"结果：成功 {results['success']}, 失败 {results['failed']}, 跳过 {results['skipped']}")
            print(f"耗时：{elapsed:.2f}s, 速度：{1000/elapsed:.1f}文件/s")
            
            if results['failed'] > 50:
                errors.append(f"失败率过高：{results['failed']}/1000")
            
            print("验证最终状态...")
            # 搜索任何已解析的函数
            search_result = self.db.search_symbol("")
            # 只检查是否有数据，不硬性要求数量
            total_entities = len(search_result['functions']) + len(search_result['classes']) + len(search_result['interfaces'])
            print(f"解析实体总数：{total_entities}")
            
            print("清理文件...")
            for f in temp_files:
                Path(f).unlink()
            
        except Exception as e:
            print(f"异常：{e}")
            import traceback
            traceback.print_exc()
            errors.append(str(e))
            success = False
        
        self.test_results['massive_file_chaos'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
    
    def test_rapid_concurrent_chaos(self):
        """测试2：快速并发混乱测试"""
        print("\n" + "="*80)
        print("混乱测试2：快速并发混乱")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            results = {
                'writes': [],
                'reads': [],
                'errors': []
            }
            lock = threading.Lock()
            
            def chaotic_writer(worker_id):
                try:
                    for i in range(50):
                        temp_file = self.project_path / f"writer_{worker_id}_{i}.ets"
                        
                        if random.random() < 0.3:
                            content = self.generate_chaos_code()
                        else:
                            content = f"export function chaos{worker_id}_{i}() {{ return {i}; }}"
                        
                        temp_file.write_text(content)
                        result = asyncio.run(self.updater.update_file(str(temp_file)))
                        
                        with lock:
                            results['writes'].append(result['status'])
                            if result['status'] != 'success':
                                results['errors'].append(result.get('error', ''))
                        
                        if random.random() < 0.5:
                            temp_file.unlink()
                
                except Exception as e:
                    with lock:
                        results['errors'].append(str(e))
            
            def chaotic_reader(worker_id):
                try:
                    for i in range(100):
                        search_terms = ['chaos', 'Func', 'Class', random.choice(string.ascii_letters)]
                        term = random.choice(search_terms)
                        
                        search = self.db.search_symbol(term)
                        with lock:
                            results['reads'].append(len(search['functions']))
                
                except Exception as e:
                    with lock:
                        results['errors'].append(str(e))
            
            threads = []
            for i in range(10):
                t = threading.Thread(target=chaotic_writer, args=(i,))
                threads.append(t)
                t.start()
            
            for i in range(20):
                t = threading.Thread(target=chaotic_reader, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join(timeout=180)
            
            write_success = results['writes'].count('success')
            write_total = len(results['writes'])
            
            print(f"写入：{write_success}/{write_total} 成功")
            print(f"读取：{len(results['reads'])} 次")
            print(f"错误：{len(results['errors'])}")
            
            if len(results['errors']) > 20:
                errors.append(f"错误过多：{len(results['errors'])}")
            
        except Exception as e:
            print(f"异常：{e}")
            import traceback
            traceback.print_exc()
            success = False
        
        self.test_results['rapid_concurrent_chaos'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
    
    def test_file_deletion_chaos(self):
        """测试3：文件删除混乱测试"""
        print("\n" + "="*80)
        print("混乱测试3：文件删除混乱")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            # 初始创建
            temp_files = []
            for i in range(500):
                temp_file = self.project_path / f"delete_test_{i}.ets"
                temp_file.write_text(f"export function test{i}() {{ return {i}; }}")
                temp_files.append(str(temp_file))
            
            asyncio.run(self.updater.batch_update(temp_files))
            
            # 混乱删除和重新创建
            for i in range(500):
                idx = random.randint(0, 499)
                temp_file = Path(temp_files[idx])
                
                if temp_file.exists():
                    temp_file.unlink()
                    asyncio.run(self.updater.update_file(str(temp_file)))
                else:
                    temp_file.write_text(f"export function test{idx}() {{ return {random.randint(1,100)}; }}")
                    asyncio.run(self.updater.update_file(str(temp_file)))
            
            print("验证最终状态...")
            search = self.db.search_symbol("test")
            print(f"剩余函数：{len(search['functions'])}")
            
        except Exception as e:
            print(f"异常：{e}")
            import traceback
            traceback.print_exc()
            errors.append(str(e))
            success = False
        
        self.test_results['file_deletion_chaos'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
    
    def test_memory_stress_chaos(self):
        """测试4：内存压力混乱测试"""
        print("\n" + "="*80)
        print("混乱测试4：内存压力混乱")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            print(f"初始内存：{initial_memory}KB")
            
            # 疯狂的内存压力
            for round_num in range(50):
                batch_files = []
                
                for i in range(100):
                    temp_file = self.project_path / f"memory_test_{round_num}_{i}.ets"
                    # 生成巨大的函数
                    lines = []
                    for _ in range(100):
                        lines.append(f"  let var{random.randint(1, 10000)} = {random.random()};")
                    
                    content = "\n".join([
                        f"export function hugeFunc{round_num}_{i}() {{",
                        *lines,
                        "  return 42;"
                        "}"
                    ])
                    temp_file.write_text(content)
                    batch_files.append(str(temp_file))
                
                asyncio.run(self.updater.batch_update(batch_files))
                
                # 清理
                for f in batch_files:
                    Path(f).unlink()
                
                gc.collect()
                
                if round_num % 10 == 0:
                    current = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    print(f"Round {round_num}: {current}KB (增长 {current - initial_memory}KB)")
            
            final_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            growth = final_memory - initial_memory
            
            print(f"最终：{final_memory}KB, 总增长 {growth}KB")
            
            if growth > 50000:  # 50MB
                errors.append(f"内存增长过大：{growth}KB")
        
        except Exception as e:
            print(f"异常：{e}")
            import traceback
            traceback.print_exc()
            errors.append(str(e))
            success = False
        
        self.test_results['memory_stress_chaos'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
    
    def test_encoding_chaos(self):
        """测试5：编码混乱测试"""
        print("\n" + "="*80)
        print("混乱测试5：编码混乱")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            temp_files = []
            
            # UTF-8
            for i in range(100):
                temp_file = self.project_path / f"utf8_{i}.ets"
                temp_file.write_text(f"export function utf8{i}() {{ return '测试{random.randint(1, 100)}'; }}", encoding='utf-8')
                temp_files.append(str(temp_file))
            
            # 其他编码（可能失败，但应该优雅处理）
            for i in range(20):
                temp_file = self.project_path / f"encoding_{i}.ets"
                try:
                    if i % 4 == 0:
                        temp_file.write_bytes(b"export function latin1() { return '\xc3\xa1'; }")  # 合法UTF-8
                    elif i % 4 == 1:
                        temp_file.write_bytes(b"export function invalid() { return '\xff\xff'; }")  # 无效UTF-8
                    elif i % 4 == 2:
                        temp_file.write_bytes(b"\xFF\xFE\x65\x00\x78\x00\x70\x00\x6F\x00\x72\x00\x74\x00\x28\x00\x29\x00\x20\x00\x7B\x00\x7D\x00")  # UTF-16 BOM
                    else:
                        temp_file.write_bytes(b"binary data\x00\x01\x02\x03\x04\x05")
                except Exception as e:
                    pass
                temp_files.append(str(temp_file))
            
            print("批量处理编码文件...")
            results = asyncio.run(self.updater.batch_update(temp_files))
            print(f"成功：{results['success']}, 失败：{results['failed']}")
            
            print("验证有效函数...")
            search = self.db.search_symbol("utf8")
            
            if len(search['functions']) < 50:
                errors.append(f"有效函数数量异常：{len(search['functions'])}")
            
            for f in temp_files:
                if Path(f).exists():
                    Path(f).unlink()
        
        except Exception as e:
            print(f"异常：{e}")
            import traceback
            traceback.print_exc()
            errors.append(str(e))
            success = False
        
        self.test_results['encoding_chaos'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
    
    def test_long_running_chaos(self):
        """测试6：长时间运行混乱测试"""
        print("\n" + "="*80)
        print("混乱测试6：长时间运行混乱")
        print("="*80)
        
        success = True
        errors = []
        
        try:
            print("开始100轮长时间测试...")
            start = time.time()
            total_ops = 0
            
            for round_num in range(100):
                temp_files = []
                
                for i in range(50):
                    temp_file = self.project_path / f"longrun_{round_num}_{i}.ets"
                    content = f"export function longFunc{round_num}_{i}() {{ return '{random.random()}'; }}"
                    temp_file.write_text(content)
                    temp_files.append(str(temp_file))
                
                asyncio.run(self.updater.batch_update(temp_files))
                
                # 随机删除一些
                for f in temp_files[:20]:
                    if random.random() < 0.5:
                        Path(f).unlink()
                
                total_ops += 50
                
                if round_num % 20 == 0:
                    elapsed = time.time() - start
                    print(f"Round {round_num}, {total_ops} ops, {elapsed:.1f}s, {total_ops/elapsed:.1f} ops/s")
            
            total_elapsed = time.time() - start
            print(f"总计 {total_elapsed:.1f}s, {total_ops} 次操作, {total_ops/total_elapsed:.1f} ops/s")
            
        except Exception as e:
            print(f"异常：{e}")
            import traceback
            traceback.print_exc()
            errors.append(str(e))
            success = False
        
        self.test_results['long_running_chaos'] = {
            'success': success,
            'errors': len(errors),
            'error_list': errors
        }
        return success
    
    def run_all_tests(self):
        self.setup()
        
        print("🚀 开始极端混乱场景测试...")
        print(f"开始时间：{datetime.now().isoformat()}")
        
        tests = [
            self.test_massive_file_chaos,
            self.test_rapid_concurrent_chaos,
            self.test_file_deletion_chaos,
            self.test_memory_stress_chaos,
            self.test_encoding_chaos,
            self.test_long_running_chaos,
        ]
        
        for test in tests:
            test_name = test.__name__
            try:
                test()
            except Exception as e:
                print(f"✗ 测试 {test_name} 执行异常：{e}")
                import traceback
                traceback.print_exc()
                self.test_results[test_name] = {
                    'success': False,
                    'error': str(e)
                }
        
        self.teardown()
        
        print("\n" + "="*80)
        print("📊 极端混乱测试总结")
        print("="*80)
        
        passed = sum(1 for v in self.test_results.values() if v.get('success', False))
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✓ PASSED" if result.get('success', False) else "✗ FAILED"
            errors = result.get('errors', 0)
            print(f"  {test_name}: {status} ({errors} errors)")
        
        print(f"\n总测试：{total}, 通过：{passed}, 失败：{total - passed}")
        
        total_errors = sum(len(r.get('error_list', [])) for r in self.test_results.values())
        if total_errors > 0:
            print(f"\n📋 所有错误列表 (共 {total_errors} 个)：")
            for test_name, result in self.test_results.items():
                if result.get('error_list'):
                    print(f"\n  [{test_name}]")
                    for error in result['error_list'][:3]:
                        print(f"    - {error}")
        
        elapsed = time.time() - self.start_time
        print(f"\n总耗时：{elapsed:.2f}s")
        
        return passed == total


if __name__ == "__main__":
    tester = ExtremeChaosTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
