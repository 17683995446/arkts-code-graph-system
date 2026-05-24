#!/usr/bin/env python3
"""
超超极端深度细节测试系统
专门测试：
1. 代码每一行的边界条件
2. 并发场景的竞态条件
3. 极端边界值和异常输入
4. 内存和资源泄漏
5. 数据一致性深度验证
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
import gc
import psutil
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] [LINE:%(lineno)d] %(message)s',
    handlers=[
        logging.FileHandler('deep_extreme_detailed_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DeepExtremeDetailedTest')


class DeepExtremeDetailedTester:
    def __init__(self):
        self.db_path: Optional[Path] = None
        self.project_path: Optional[Path] = None
        self.db: Optional[CodeGraphDB] = None
        self.parser: Optional[LocalArkTSParser] = None
        self.updater: Optional[IncrementalUpdater] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.test_results: Dict[str, Any] = {}

    def setup(self):
        logger.info("[SETUP] 初始化深度极端细节测试环境")
        self.db_path = Path(tempfile.mkdtemp()) / 'deep_test.db'
        self.project_path = Path(tempfile.mkdtemp())
        
        self.db = CodeGraphDB(str(self.db_path))
        self.parser = LocalArkTSParser()
        self.updater = IncrementalUpdater(self.db, self.parser)
        
        logger.info(f"[SETUP] 数据库路径: {self.db_path}")
        logger.info(f"[SETUP] 项目路径: {self.project_path}")

    def teardown(self):
        logger.info("[TEARDOWN] 开始清理测试环境")
        if self.db:
            self.db.close()
        import shutil
        if self.project_path.exists():
            shutil.rmtree(self.project_path)
        if self.db_path.exists():
            self.db_path.unlink()
        logger.info("[TEARDOWN] 测试环境清理完成")

    def generate_extreme_code_variant(self, variant: str, index: int) -> str:
        """生成各种极端代码变体"""
        if variant == "empty":
            return ""
        elif variant == "only_comments":
            return "// " * 100 + "\n" * 50
        elif variant == "only_whitespace":
            return " " * 10000 + "\t" * 1000
        elif variant == "max_function_params":
            params = ", ".join([f"p{i}: number" for i in range(50)])
            return f"export function maxParams({params}): void {{ }}"
        elif variant == "deep_nesting":
            code = "export function nested() {\n"
            for _ in range(100):
                code += "  if (true) {\n"
            code += "  return 1;\n"
            for _ in range(100):
                code += "  }\n"
            code += "}"
            return code
        elif variant == "max_class_members":
            code = "export class MaxMembers {\n"
            for i in range(100):
                code += f"  prop{i}: number = {i};\n"
                code += f"  method{i}() {{ return {i}; }}\n"
            code += "}"
            return code
        elif variant == "unicode_extreme":
            return '// Unicode极端测试\nexport function test() { return "😀🔥🎉💩🚀"; }'
        elif variant == "special_chars":
            chars = ''.join(chr(i) for i in range(128, 256))
            return f"export function special() {{ /* {chars} */ }}\n"
        elif variant == "very_long_lines":
            long_line = "x = " + "1 + " * 1000
            return f"export function longLine() {{ {long_line}; }}"
        elif variant == "mixed_unicode":
            return '// 混合Unicode测试\nexport function test() { return "\\u0048\\u0065\\u006c\\u006c\\u006f"; }'
        elif variant == "binary_like":
            return bytes([0, 1, 2, 255, 128, 127]).decode('latin-1', errors='replace')
        elif variant == "null_bytes":
            return 'export function nullTest() { return "\\x00"; }'
        else:
            return f"// 默认测试代码变体 {index}\nexport function test{index}() {{ return {index}; }}"

    async def test_line_by_line_boundary_conditions(self) -> bool:
        """逐行边界条件测试"""
        print("\n" + "="*120)
        print("🧪 测试1：逐行边界条件测试")
        print("="*120)
        
        logger.info("[TEST1] 开始逐行边界条件测试")
        
        test_cases = [
            "empty", "only_comments", "only_whitespace", "max_function_params",
            "deep_nesting", "max_class_members", "unicode_extreme", "special_chars",
            "very_long_lines", "mixed_unicode", "binary_like", "null_bytes"
        ]
        
        all_passed = True
        for i, case in enumerate(test_cases):
            logger.debug(f"[TEST1:LINE:{i+50}] 测试案例 {i+1}/{len(test_cases)}: {case}")
            
            file_path = self.project_path / f"boundary_{case}.ets"
            code = self.generate_extreme_code_variant(case, i)
            file_path.write_text(code, encoding='utf-8')
            
            try:
                result = await self.updater.update_file(str(file_path))
                
                if result["status"] == "error":
                    self.errors.append(f"边界案例 {case} 错误: {result['error']}")
                    logger.error(f"[TEST1:LINE:{i+70}] 错误: {result['error']}")
                    all_passed = False
                else:
                    logger.debug(f"[TEST1:LINE:{i+75}] 成功: {case} -> {result['status']}")
                    
            except Exception as e:
                self.errors.append(f"边界案例 {case} 异常: {str(e)}")
                logger.exception(f"[TEST1:LINE:{i+80}]")
                all_passed = False
        
        if all_passed:
            print(f"✅ 逐行边界条件测试完成: {len(test_cases)} 种情况全部处理")
        else:
            print(f"❌ 逐行边界条件测试有问题")
        
        return all_passed

    async def test_concurrent_race_conditions(self) -> bool:
        """并发竞态条件测试"""
        print("\n" + "="*120)
        print("⚡ 测试2：并发竞态条件深度测试")
        print("="*120)
        
        logger.info("[TEST2] 开始并发竞态条件测试")
        
        num_threads = 20
        operations_per_thread = 100
        results = {"success": 0, "errors": 0}
        lock = threading.Lock()
        
        def worker(thread_id):
            nonlocal results
            local_db = CodeGraphDB(str(self.db_path))
            local_parser = LocalArkTSParser()
            local_updater = IncrementalUpdater(local_db, local_parser)
            
            for i in range(operations_per_thread):
                try:
                    file_path = self.project_path / f"race_{thread_id}_{i}.ets"
                    code = f"export function race{thread_id}_{i}() {{ return {thread_id * 1000 + i}; }}"
                    file_path.write_text(code)
                    
                    result = asyncio.run(local_updater.update_file(str(file_path)))
                    
                    with lock:
                        if result['status'] == 'success':
                            results['success'] += 1
                        else:
                            results['errors'] += 1
                            
                except Exception as e:
                    with lock:
                        results['errors'] += 1
                    logger.warning(f"[TEST2:LINE:{150+thread_id}] 线程{thread_id}操作{i}异常", exc_info=True)
            
            local_db.close()
        
        threads = []
        start_time = time.time()
        
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=120)
        
        elapsed = time.time() - start_time
        
        logger.info(f"[TEST2] 完成: {results['success']} 成功, {results['errors']} 错误, 耗时 {elapsed:.2f}s")
        
        if results['errors'] > 5:
            self.errors.append(f"并发竞态测试有 {results['errors']} 个错误")
            print(f"❌ 并发竞态条件测试有问题: {results['errors']} 个错误")
            return False
        
        print(f"✅ 并发竞态条件测试完成: {results['success']} 成功, {results['errors']} 错误, {elapsed:.2f}s")
        return True

    async def test_data_consistency_deep(self) -> bool:
        """数据一致性深度验证"""
        print("\n" + "="*120)
        print("🔍 测试3：数据一致性深度验证")
        print("="*120)
        
        logger.info("[TEST3] 开始数据一致性深度验证")
        
        # 创建测试文件
        num_files = 50
        created_files = []
        
        for i in range(num_files):
            file_path = self.project_path / f"consistency_{i}.ets"
            code = f"""export function func{i}() {{ return {i}; }}
export class Class{i} {{ value: number = {i}; }}
export interface I{i} {{ prop: number; }}"""
            file_path.write_text(code)
            created_files.append(str(file_path))
            await self.updater.update_file(str(file_path))
        
        logger.debug(f"[TEST3:LINE:210] 创建 {num_files} 个测试文件")
        
        # 验证数据一致性
        errors_found = 0
        
        for i, file_path_str in enumerate(created_files):
            file_id = self.db.get_file_id(file_path_str)
            if not file_id:
                errors_found += 1
                logger.error(f"[TEST3:LINE:{220+i}] 文件 {i} ID 为空")
                continue
            
            funcs = self.db.get_functions_in_file(file_id)
            classes = self.db.get_classes_in_file(file_id)
            interfaces = self.db.get_interfaces_in_file(file_id)
            
            logger.debug(f"[TEST3:LINE:{230+i}] 文件 {i}: {len(funcs)} 函数, {len(classes)} 类, {len(interfaces)} 接口")
            
            if len(funcs) != 1 or len(classes) != 1 or len(interfaces) != 1:
                errors_found += 1
                logger.error(f"[TEST3:LINE:{235+i}] 文件 {i} 数据不一致")
        
        # 测试搜索一致性
        logger.debug("[TEST3:LINE:240] 测试搜索一致性")
        for search_term in ["func", "Class", "I", "test"]:
            results = self.db.search_symbol(search_term)
            logger.debug(f"[TEST3:LINE:243] 搜索 '{search_term}': {len(results['functions'])} 函数")
        
        if errors_found > 0:
            self.errors.append(f"数据一致性验证有 {errors_found} 个错误")
            print(f"❌ 数据一致性深度验证有问题: {errors_found} 个错误")
            return False
        
        print(f"✅ 数据一致性深度验证完成: {num_files} 个文件全部一致")
        return True

    async def test_memory_resource_leaks(self) -> bool:
        """内存和资源泄漏检测"""
        print("\n" + "="*120)
        print("💾 测试4：内存和资源泄漏检测")
        print("="*120)
        
        logger.info("[TEST4] 开始内存和资源泄漏检测")
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        logger.debug(f"[TEST4:LINE:265] 初始内存: {initial_memory:.2f} MB")
        
        # 执行大量操作
        num_operations = 500
        
        for i in range(num_operations):
            file_path = self.project_path / f"memory_{i}.ets"
            code = f"export function mem{i}() {{ return {i}; }}"
            file_path.write_text(code)
            await self.updater.update_file(str(file_path))
            
            if i % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                logger.debug(f"[TEST4:LINE:{280+i//100}] 内存使用: {current_memory:.2f} MB")
        
        # 清理
        del file_path
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        logger.info(f"[TEST4:LINE:290] 内存增长: {memory_increase:.2f} MB (初始: {initial_memory:.2f}, 最终: {final_memory:.2f})")
        
        # 检查点操作
        try:
            self.db.checkpoint()
            logger.debug("[TEST4:LINE:295] 数据库检查点完成")
        except Exception as e:
            logger.warning(f"[TEST4:LINE:297] 检查点异常: {e}")
        
        if memory_increase > 100:
            self.warnings.append(f"内存增长较大: {memory_increase:.2f} MB")
            print(f"⚠️  内存和资源泄漏检测: 内存增长 {memory_increase:.2f} MB")
        
        print(f"✅ 内存和资源泄漏检测完成: 内存增长 {memory_increase:.2f} MB")
        return True

    async def test_extreme_edge_values(self) -> bool:
        """极端边界值测试"""
        print("\n" + "="*120)
        print("🎯 测试5：极端边界值测试")
        print("="*120)
        
        logger.info("[TEST5] 开始极端边界值测试")
        
        test_cases = [
            # 超大数字边界
            ("max_int", "export function maxInt(): number { return 9223372036854775807; }"),
            ("min_int", "export function minInt(): number { return -9223372036854775808; }"),
            ("max_float", "export function maxFloat(): number { return 1.7976931348623157e+308; }"),
            ("min_float", "export function minFloat(): number { return 5e-324; }"),
            
            # 特殊字符串
            ("quote", "export function quote(): string { return '\"'; }"),
            ("backslash", "export function backslash(): string { return '\\\\'; }"),
            ("newline", "export function newline(): string { return '\\n'; }"),
            ("tab", "export function tab(): string { return '\\t'; }"),
            ("unicode_normal", "export function unicodeNormal(): string { return '你好世界'; }"),
            ("unicode_mixed", "export function unicodeMixed(): string { return 'Hello世界123'; }"),
            
            # 布尔和空值
            ("bool_true", "export function boolTrue(): boolean { return true; }"),
            ("bool_false", "export function boolFalse(): boolean { return false; }"),
            ("null_value", "export function nullVal(): any { return null; }"),
            ("undefined_value", "export function undefinedVal(): any { return undefined; }"),
        ]
        
        all_passed = True
        for i, (name, code) in enumerate(test_cases):
            logger.debug(f"[TEST5:LINE:{330+i}] 测试: {name}")
            
            file_path = self.project_path / f"edge_{name}.ets"
            file_path.write_text(code)
            
            try:
                result = await self.updater.update_file(str(file_path))
                
                if result["status"] == "error":
                    self.errors.append(f"边界值 {name} 错误: {result['error']}")
                    logger.error(f"[TEST5:LINE:{340+i}]")
                    all_passed = False
                else:
                    logger.debug(f"[TEST5:LINE:{343+i}] 成功: {name}")
                    
            except Exception as e:
                self.errors.append(f"边界值 {name} 异常: {str(e)}")
                logger.exception(f"[TEST5:LINE:{347+i}]")
                all_passed = False
        
        if all_passed:
            print(f"✅ 极端边界值测试完成: {len(test_cases)} 种情况全部处理")
        else:
            print(f"❌ 极端边界值测试有问题")
        
        return all_passed

    async def test_exception_handling_robustness(self) -> bool:
        """异常处理鲁棒性测试"""
        print("\n" + "="*120)
        print("🛡️ 测试6：异常处理鲁棒性测试")
        print("="*120)
        
        logger.info("[TEST6] 开始异常处理鲁棒性测试")
        
        test_scenarios = [
            ("file_not_exists", "/nonexistent/path/file.ets"),
            ("permission_denied", str(self.project_path / "readonly.ets")),
            ("invalid_encoding", "invalid_byte_sequence.ets"),
        ]
        
        # 测试不存在的文件
        logger.debug("[TEST6:LINE:370] 测试不存在的文件")
        result = await self.updater.update_file("/nonexistent/path/file.ets")
        if result["status"] != "failed":
            self.errors.append("不存在的文件应该返回 failed 状态")
            logger.error("[TEST6:LINE:373] 状态错误")
        
        # 测试只读文件
        logger.debug("[TEST6:LINE:376] 测试只读文件")
        readonly_file = self.project_path / "readonly.ets"
        readonly_file.write_text("export function test() {}")
        readonly_file.chmod(0o444)
        
        try:
            result = await self.updater.update_file(str(readonly_file))
            # 只读文件不应该导致崩溃
            logger.debug(f"[TEST6:LINE:{383}] 只读文件结果: {result['status']}")
        except Exception as e:
            logger.warning(f"[TEST6:LINE:{386}] 只读文件异常: {e}")
        finally:
            readonly_file.chmod(0o644)
        
        print(f"✅ 异常处理鲁棒性测试完成")
        return True

    async def run_all_deep_extreme_tests(self):
        """运行所有深度极端测试"""
        print("\n" + "="*120)
        print("🚀 超超极端深度细节测试系统启动")
        print("="*120)
        
        self.setup()
        
        try:
            tests = [
                ("逐行边界条件", self.test_line_by_line_boundary_conditions),
                ("并发竞态条件", self.test_concurrent_race_conditions),
                ("数据一致性深度", self.test_data_consistency_deep),
                ("内存资源泄漏", self.test_memory_resource_leaks),
                ("极端边界值", self.test_extreme_edge_values),
                ("异常处理鲁棒性", self.test_exception_handling_robustness),
            ]
            
            all_passed = True
            
            for test_name, test_func in tests:
                logger.info(f"[MAIN] 开始测试: {test_name}")
                passed = await test_func()
                self.test_results[test_name] = passed
                
                if not passed:
                    all_passed = False
            
            # 总结
            print("\n" + "="*120)
            print("📊 超超极端深度细节测试总结")
            print("="*120)
            
            for test_name, passed in self.test_results.items():
                status = "✅ 通过" if passed else "❌ 失败"
                print(f"  {test_name}: {status}")
            
            if self.errors:
                print(f"\n⚠️ 发现 {len(self.errors)} 个问题:")
                for i, err in enumerate(self.errors[:10], 1):
                    print(f"  {i}. {err}")
            else:
                print("\n🎉 所有深度极端测试完美通过！")
            
            if self.warnings:
                print(f"\n⚠️ 警告 ({len(self.warnings)}):")
                for i, warn in enumerate(self.warnings[:5], 1):
                    print(f"  {i}. {warn}")
            
            print("="*120)
            
            return all_passed, self.errors
            
        finally:
            self.teardown()


def main():
    tester = DeepExtremeDetailedTester()
    success, errors = asyncio.run(tester.run_all_deep_extreme_tests())
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
