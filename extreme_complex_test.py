#!/usr/bin/env python3
"""
超级极端复杂场景测试系统
按照第一性原理进行全代码分支覆盖验证
包含：极端复杂度代码、极端并发、极端长时间运行、极端边界条件
"""
import os
import sys
import time
import random
import string
import asyncio
import tempfile
import threading
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('extreme_complex_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ExtremeComplexTester:
    def __init__(self):
        self.db_path = None
        self.project_path = None
        self.db = None
        self.parser = None
        self.updater = None
        self.errors = []
        self.test_results = {}
        
    def setup(self):
        self.db_path = Path(tempfile.mkdtemp()) / 'extreme_test.db'
        self.project_path = Path(tempfile.mkdtemp())
        self.db = CodeGraphDB(str(self.db_path))
        self.parser = LocalArkTSParser()
        self.updater = IncrementalUpdater(self.db, self.parser)
        logger.info(f"[EXTREME] 测试环境设置完成: db={self.db_path}, project={self.project_path}")
        
    def teardown(self):
        if self.db:
            self.db.close()
        import shutil
        if self.project_path.exists():
            shutil.rmtree(self.project_path)
        if self.db_path.exists():
            self.db_path.unlink()
        logger.info("[EXTREME] 测试环境清理完成")
        
    def generate_extreme_complex_code(self, complexity: int = 10) -> str:
        """生成极端复杂的 ArkTS 代码"""
        parts = []
        
        # 极端复杂的导入语句
        for i in range(complexity):
            parts.append(f"import {{ Module{i}, Type{i}, Func{i} }} from '@ohos/module{i}'\n")
        
        # 极端复杂的接口
        for i in range(complexity // 2):
            extends_list = ", ".join([f"IBase{j}" for j in range(i)]) if i > 0 else ""
            parts.append(f"interface IBase{i} {{{extends_list} {'' if i==0 else ','}\n")
            for j in range(10):
                parts.append(f"  prop{j}: Type{i} | null | undefined\n")
            parts.append("}\n")
        
        # 极端复杂的泛型接口
        parts.append("\ninterface IGeneric<T extends string | number, U = unknown> {\n")
        parts.append("  value: T\n")
        parts.append("  data: U[]\n")
        parts.append("  meta: Record<string, T | U>\n")
        parts.append("}\n")
        
        # 极端复杂的组件
        parts.append("\n@Entry\n@Component\nstruct MegaComponent {\n")
        for i in range(20):
            parts.append(f"  @State state{i}: number = {i}\n")
            parts.append(f"  @Prop prop{i}: string = 'prop{i}'\n")
            parts.append(f"  @Link link{i}: boolean = {i % 2 == 0}\n")
        
        # 复杂的 build 方法
        parts.append("\n  build() {\n")
        parts.append("    Column() {\n")
        for i in range(10):
            text_content = "      Text(`State " + str(i) + ": ${this.state" + str(i) + "}`)\n"
            parts.append(text_content)
            parts.append(f"        .fontSize({12 + i})\n")
            click_handler = "        .onClick(() => {{ this.state" + str(i) + "++ }})\n"
            parts.append(click_handler)
        parts.append("    }\n")
        parts.append("  }\n\n")
        
        # 极端复杂的方法
        for i in range(15):
            params = ", ".join([f"p{j}: Type{i} = {j}" for j in range(5)])
            parts.append(f"  method{i}({params}): IGeneric<string, number> {{\n")
            parts.append(f"    return {{ value: 'test{i}', data: [{i}], meta: {{ key: {i} }} }}\n")
            parts.append("  }\n")
        
        parts.append("}\n")
        
        # 极端复杂的类
        for i in range(complexity // 3):
            parts.append(f"\nexport class ComplexClass{i} implements IBase{i % 5} {{\n")
            parts.append(f"  private _privateField{i}: string = 'private{i}'\n")
            parts.append(f"  public publicField{i}: number = {i}\n")
            
            for j in range(8):
                async_suffix = "async " if j % 2 == 0 else ""
                parts.append(f"  {async_suffix}method{j}(): void {{\n")
                parts.append(f"    console.log('ComplexClass{i}.method{j}')\n")
                parts.append("  }\n")
            
            parts.append("}\n")
        
        # 极端复杂的函数
        for i in range(20):
            return_type = f"Promise<IGeneric<string, {i}>>" if i % 3 == 0 else f"string | null | undefined"
            parts.append(f"\nexport async function extremeFunction{i}(input: string): {return_type} {{\n")
            parts.append(f"  const result = input.toUpperCase() + '{i}'\n")
            parts.append("  return result\n")
            parts.append("}\n")
        
        return ''.join(parts)
    
    def test_extreme_complex_code_parsing(self):
        """测试极端复杂代码解析"""
        logger.info("[EXTREME_TEST] 开始极端复杂代码解析测试")
        try:
            # 创建极端复杂的代码文件
            complex_file = self.project_path / "extreme_complex.ets"
            code = self.generate_extreme_complex_code(15)
            complex_file.write_text(code)
            
            logger.info(f"[EXTREME_TEST] 生成代码长度: {len(code)} 字符")
            
            # 解析这个极端复杂的文件
            result = asyncio.run(self.updater.update_file(str(complex_file)))
            
            if result['status'] != 'success':
                self.errors.append(f"极端复杂代码解析失败: {result.get('error')}")
                logger.error(f"[EXTREME_TEST] 极端复杂代码解析失败: {result.get('error')}")
                return False
            
            logger.info(f"[EXTREME_TEST] 极端复杂代码解析成功: {result}")
            return True
        except Exception as e:
            self.errors.append(f"极端复杂代码解析异常: {str(e)}")
            logger.exception("[EXTREME_TEST] 极端复杂代码解析异常")
            return False
    
    def test_extreme_concurrency(self):
        """测试极端并发场景"""
        logger.info("[EXTREME_TEST] 开始极端并发测试")
        try:
            num_threads = 10
            num_files_per_thread = 20
            results = []
            errors = []
            
            def worker(thread_id):
                try:
                    local_db = CodeGraphDB(str(self.db_path))
                    local_parser = LocalArkTSParser()
                    local_updater = IncrementalUpdater(local_db, local_parser)
                    
                    for i in range(num_files_per_thread):
                        file_path = self.project_path / f"thread_{thread_id}_file_{i}.ets"
                        code = f"""@Component
struct Thread{thread_id}Component{i} {{
  @State value: number = {thread_id * 100 + i}
  build() {{ Text('Thread {thread_id}, File {i}') }}
}}
"""
                        file_path.write_text(code)
                        result = asyncio.run(local_updater.update_file(str(file_path)))
                        if result['status'] != 'success':
                            errors.append(f"Thread {thread_id}, File {i}: {result.get('error')}")
                    
                    local_db.close()
                    results.append(f"Thread {thread_id} completed successfully")
                except Exception as e:
                    errors.append(f"Thread {thread_id} exception: {str(e)}")
            
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join(timeout=60)
            
            if errors:
                self.errors.extend(errors)
                logger.error(f"[EXTREME_TEST] 极端并发测试发现 {len(errors)} 个错误")
                return False
            
            logger.info(f"[EXTREME_TEST] 极端并发测试完成: {num_threads} 线程, {num_files_per_thread} 文件/线程")
            return True
        except Exception as e:
            self.errors.append(f"极端并发测试异常: {str(e)}")
            logger.exception("[EXTREME_TEST] 极端并发测试异常")
            return False
    
    def test_extreme_long_duration(self):
        """测试极端长时间运行"""
        logger.info("[EXTREME_TEST] 开始极端长时间运行测试")
        try:
            duration_seconds = 30
            updates_done = 0
            file_path = self.project_path / "long_running.ets"
            start_time = time.time()
            
            while time.time() - start_time < duration_seconds:
                updates_done += 1
                
                # 每次都生成不同的代码
                code = f"""@Component
struct LongRunningComponent{updates_done} {{
  @State iteration: number = {updates_done}
  @State timestamp: number = {int(time.time())}
  build() {{ Text('Iteration {updates_done}') }}
  method{updates_done}(): string {{ return 'result{updates_done}' }}
}}
"""
                file_path.write_text(code)
                
                result = asyncio.run(self.updater.update_file(str(file_path)))
                
                if result['status'] not in ['success', 'skipped']:
                    self.errors.append(f"长时间运行在第 {updates_done} 次失败: {result.get('error')}")
                    return False
                
                # 随机检查数据库一致性
                if updates_done % 20 == 0:
                    search_result = self.db.search_symbol(f"LongRunningComponent{updates_done}")
                    if not search_result['classes']:
                        self.errors.append(f"长时间运行: 数据库搜索失败，第 {updates_done} 次")
                        return False
            
            elapsed = time.time() - start_time
            logger.info(f"[EXTREME_TEST] 长时间运行测试完成: {updates_done} 次更新, {elapsed:.2f} 秒, {updates_done/elapsed:.2f} 次/秒")
            return True
        except Exception as e:
            self.errors.append(f"长时间运行测试异常: {str(e)}")
            logger.exception("[EXTREME_TEST] 长时间运行测试异常")
            return False
    
    def test_extreme_boundary_conditions(self):
        """测试极端边界条件"""
        logger.info("[EXTREME_TEST] 开始极端边界条件测试")
        try:
            test_cases = [
                ("empty_file", ""),
                ("minimal_code", "export {}"),
                ("max_name_length", f"export function {'a' * 500}(): void {{}}"),
                ("special_chars", 'export function test(): string { return "🔥💩🦄\\u0000\\uFFFF"; }'),
                ("deep_nesting", "{\n" * 100 + "}\n" * 100),
                ("extreme_whitespace", " " * 10000 + "export function test() {}"),
                ("unicode_bom", "\ufeffexport function test() {}"),
                ("mixed_line_endings", "export function test() {}\r\n// comment\nfunction test2() {}\n"),
            ]
            
            for name, code in test_cases:
                file_path = self.project_path / f"boundary_{name}.ets"
                file_path.write_text(code)
                
                result = asyncio.run(self.updater.update_file(str(file_path)))
                
                if result['status'] not in ['success', 'skipped']:
                    self.errors.append(f"边界条件测试 '{name}' 失败: {result.get('error')}")
                    logger.error(f"[EXTREME_TEST] 边界条件 '{name}' 失败")
                else:
                    logger.info(f"[EXTREME_TEST] 边界条件 '{name}' 通过")
            
            return True
        except Exception as e:
            self.errors.append(f"边界条件测试异常: {str(e)}")
            logger.exception("[EXTREME_TEST] 边界条件测试异常")
            return False
    
    def test_extreme_error_scenarios(self):
        """测试极端错误场景"""
        logger.info("[EXTREME_TEST] 开始极端错误场景测试")
        try:
            # 测试1：文件不存在
            result = asyncio.run(self.updater.update_file("/nonexistent/path/file.ets"))
            if result['status'] != 'failed':
                self.errors.append("不存在的文件应该返回 failed 状态")
            
            # 测试2：权限问题（尝试写入只读文件）
            try:
                read_only_file = self.project_path / "read_only.ets"
                read_only_file.write_text("export function test() {}")
                read_only_file.chmod(0o444)
                
                # 更新应该成功，因为我们只是读取
                result = asyncio.run(self.updater.update_file(str(read_only_file)))
                if result['status'] not in ['success', 'skipped']:
                    self.errors.append(f"只读文件测试失败: {result.get('error')}")
            finally:
                read_only_file.chmod(0o644)
            
            # 测试3：无效的代码格式
            invalid_file = self.project_path / "invalid.ets"
            invalid_file.write_text("function test() {")  # 未闭合的括号
            result = asyncio.run(self.updater.update_file(str(invalid_file)))
            # 即使代码无效，解析器也应该处理而不崩溃
            logger.info(f"[EXTREME_TEST] 无效代码测试结果: {result['status']}")
            
            logger.info("[EXTREME_TEST] 极端错误场景测试完成")
            return True
        except Exception as e:
            self.errors.append(f"极端错误场景测试异常: {str(e)}")
            logger.exception("[EXTREME_TEST] 极端错误场景测试异常")
            return False
    
    def test_extreme_mixed_workload(self):
        """测试极端混合工作负载"""
        logger.info("[EXTREME_TEST] 开始极端混合工作负载测试")
        try:
            # 创建大量各种类型的文件
            num_files = 100
            files = []
            
            for i in range(num_files):
                complexity = i % 5
                file_path = self.project_path / f"mix_{i}.ets"
                
                if complexity == 0:
                    # 简单函数
                    code = f"export function func{i}(): number {{ return {i}; }}"
                elif complexity == 1:
                    # 简单组件
                    code = f"""@Component
struct Comp{i} {{
  build() {{ Text('Comp{i}') }}
}}"""
                elif complexity == 2:
                    # 带状态的组件
                    code = "@Entry\n@Component\nstruct EntryComp" + str(i) + " {\n  @State count: number = " + str(i) + "\n  build() { Text(`Count: ${this.count}`) }\n}"
                elif complexity == 3:
                    # 接口和类
                    code = f"""interface IInterface{i} {{ value: number; }}
class Class{i} implements IInterface{i} {{ value: number = {i}; }}"""
                else:
                    # 复杂混合
                    code = self.generate_extreme_complex_code(3)
                
                file_path.write_text(code)
                files.append(str(file_path))
            
            # 批量更新
            result = asyncio.run(self.updater.batch_update(files))
            
            if result['failed'] > 5:
                self.errors.append(f"混合工作负载测试失败: {result['failed']} 个文件失败")
                return False
            
            logger.info(f"[EXTREME_TEST] 混合工作负载测试完成: {result}")
            return True
        except Exception as e:
            self.errors.append(f"混合工作负载测试异常: {str(e)}")
            logger.exception("[EXTREME_TEST] 混合工作负载测试异常")
            return False
    
    def run_all_extreme_tests(self):
        """运行所有极端测试"""
        print("\n" + "="*120)
        print("🌪️ 超级极端复杂场景测试系统")
        print("="*120)
        print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.setup()
        
        tests = [
            ("极端复杂代码解析", self.test_extreme_complex_code_parsing),
            ("极端并发测试", self.test_extreme_concurrency),
            ("极端长时间运行", self.test_extreme_long_duration),
            ("极端边界条件", self.test_extreme_boundary_conditions),
            ("极端错误场景", self.test_extreme_error_scenarios),
            ("极端混合工作负载", self.test_extreme_mixed_workload),
        ]
        
        all_passed = True
        
        for test_name, test_func in tests:
            print(f"\n▶️ 运行: {test_name}")
            start_time = time.time()
            
            try:
                passed = test_func()
                elapsed = time.time() - start_time
                
                if passed:
                    print(f"✅ {test_name} 通过! 耗时: {elapsed:.2f}s")
                else:
                    print(f"❌ {test_name} 失败!")
                    all_passed = False
            except Exception as e:
                print(f"❌ {test_name} 异常: {str(e)}")
                all_passed = False
        
        self.teardown()
        
        print("\n" + "="*120)
        print("📊 超级极端复杂场景测试总结")
        print("="*120)
        
        if self.errors:
            print(f"\n⚠️ 发现 {len(self.errors)} 个问题:")
            for i, error in enumerate(self.errors[:10], 1):
                print(f"   {i}. {error}")
            if len(self.errors) > 10:
                print(f"   ... 还有 {len(self.errors) - 10} 个问题")
        else:
            print("\n🎉 所有极端测试通过！系统质量优秀！")
        
        print(f"\n测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*120)
        
        return all_passed, self.errors


def main():
    tester = ExtremeComplexTester()
    success, errors = tester.run_all_extreme_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
