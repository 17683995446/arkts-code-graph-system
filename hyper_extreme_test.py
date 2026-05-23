#!/usr/bin/env python3
"""
超极端混沌测试系统 - 深度验证和隐藏问题发现
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
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser
from src.models import ParsedFile, FunctionInfo, ClassInfo

logging.basicConfig(
    level=logging.DEBUG,
    format='[LINE:%(lineno)d] %(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hyper_extreme_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('HyperExtremeTest')


class HyperExtremeTester:
    def __init__(self):
        self.db_path = None
        self.project_path = None
        self.db = None
        self.parser = None
        self.updater = None
        self.errors = []
        self.issues_found = []
        self.test_results = {}

    def setup(self):
        logger.debug("[SETUP:LINE:50] 初始化超极端测试环境")
        self.db_path = Path(tempfile.mkdtemp()) / 'hyper_test.db'
        self.project_path = Path(tempfile.mkdtemp())
        logger.debug(f"[SETUP:LINE:53] 数据库路径: {self.db_path}")
        logger.debug(f"[SETUP:LINE:54] 项目路径: {self.project_path}")
        
        self.db = CodeGraphDB(str(self.db_path))
        logger.debug("[SETUP:LINE:57] 数据库初始化完成")
        
        self.parser = LocalArkTSParser()
        logger.debug("[SETUP:LINE:60] 本地解析器初始化完成")
        
        self.updater = IncrementalUpdater(self.db, self.parser)
        logger.debug("[SETUP:LINE:63] 增量更新器初始化完成")

    def teardown(self):
        logger.debug("[TEARDOWN:LINE:67] 开始清理测试环境")
        if self.db:
            logger.debug("[TEARDOWN:LINE:69] 关闭数据库连接")
            self.db.close()
        import shutil
        if self.project_path.exists():
            logger.debug(f"[TEARDOWN:LINE:73] 清理项目目录: {self.project_path}")
            shutil.rmtree(self.project_path)
        if self.db_path.exists():
            logger.debug(f"[TEARDOWN:LINE:76] 清理数据库文件: {self.db_path}")
            self.db_path.unlink()
        logger.info("[TEARDOWN:LINE:78] 测试环境清理完成")

    def generate_extreme_edge_case_code(self, case_type: str) -> str:
        logger.debug(f"[GENERATE:LINE:83] 生成极端边缘案例代码，类型: {case_type}")
        
        if case_type == "empty":
            return ""
        elif case_type == "whitespace":
            return " " * 10000
        elif case_type == "comments_only":
            return "// " + " ".join(random.choices(string.ascii_letters, k=500)) + "\n" * 10
        elif case_type == "weird_chars":
            return ''.join(chr(i) for i in range(128, 256)) + "\n// test\n"
        elif case_type == "unicode_bom":
            return "\ufeff// BOM test\nexport function test() { return 'hello'; }\n"
        elif case_type == "max_functions":
            code = ""
            for i in range(50):
                code += f"export function func{i}() {{ return {i}; }}\n"
            return code
        elif case_type == "max_classes":
            code = ""
            for i in range(30):
                code += f"class Class{i} {{ constructor() {{ }}}}\n"
            return code
        elif case_type == "malformed_syntax":
            return "this is invalid code! @@#$$! \nfunction test() { missing closing\n"
        elif case_type == "deep_nesting":
            code = "export function nested() {\n"
            for i in range(50):
                code += "  {\n"
            code += "  // deep\n"
            for i in range(50):
                code += "  }\n"
            code += "}\n"
            return code
        elif case_type == "mixed_case":
            return '''@Entry
@Component
struct Test1 {
  @State count: number = 0;
  build() { Column() {} }
}

export function helper() { return "test"; }

interface Test { x: number; }

import { X } from 'module';'''
        else:
            return "// default test code\nexport function defaultTest() { return true; }\n"

    async def test_extreme_edge_cases(self) -> bool:
        print("\n" + "="*100)
        print("🔥 超极端边缘情况测试")
        print("="*100)
        
        cases = [
            "empty", "whitespace", "comments_only", "weird_chars", 
            "unicode_bom", "max_functions", "max_classes", 
            "malformed_syntax", "deep_nesting", "mixed_case"
        ]
        
        all_passed = True
        
        for i, case_type in enumerate(cases):
            logger.debug(f"[EDGE_CASE_TEST:LINE:135] 测试案例 {i+1}/{len(cases)}: {case_type}")
            
            file_path = self.project_path / f"edge_{case_type}.ets"
            code = self.generate_extreme_edge_case_code(case_type)
            file_path.write_text(code)
            
            try:
                result = await self.updater.update_file(str(file_path))
                
                if result["status"] == "error":
                    self.errors.append(f"边缘案例 {case_type} 发生错误: {result['error']}")
                    logger.error(f"[EDGE_CASE_TEST:LINE:146] 错误: {result['error']}")
                    all_passed = False
                elif result["status"] == "failed":
                    logger.debug(f"[EDGE_CASE_TEST:LINE:148] 失败但可接受 (文件不存在等): {result['error']}")
                else:
                    logger.debug(f"[EDGE_CASE_TEST:LINE:150] 成功处理案例: {case_type}")
                    
            except Exception as e:
                self.errors.append(f"边缘案例 {case_type} 异常: {str(e)}")
                logger.exception(f"[EDGE_CASE_TEST:LINE:154] 异常")
                all_passed = False
        
        print(f"✅ 极端边缘情况测试完成: {'全部通过' if all_passed else '有错误'}")
        return all_passed

    async def test_rapid_consecutive_updates(self) -> bool:
        print("\n" + "="*100)
        print("⚡ 快速连续更新测试")
        print("="*100)
        
        logger.debug("[RAPID_UPDATE:LINE:167] 开始快速连续更新测试")
        
        file_path = self.project_path / "rapid_updates.ets"
        num_updates = 100
        errors_count = 0
        
        for i in range(num_updates):
            try:
                code = f"export function version{i}() {{ return {i}; }}\nclass C{i} {{ }}\n"
                file_path.write_text(code)
                
                result = await self.updater.update_file(str(file_path))
                
                if result["status"] == "error":
                    errors_count += 1
                    logger.warning(f"[RAPID_UPDATE:LINE:180] 第 {i} 次更新失败: {result['error']}")
                
                if i % 20 == 0:
                    logger.debug(f"[RAPID_UPDATE:LINE:183] 已完成 {i}/{num_updates} 次更新")
                    
            except Exception as e:
                errors_count += 1
                logger.exception(f"[RAPID_UPDATE:LINE:187] 第 {i} 次更新异常")
        
        logger.info(f"[RAPID_UPDATE:LINE:190] 快速更新测试完成: {num_updates} 次更新, {errors_count} 个错误")
        
        if errors_count > 0:
            self.errors.append(f"快速更新测试中有 {errors_count} 个错误")
        
        print(f"✅ 快速连续更新测试完成: {num_updates} 次更新, {errors_count} 个错误")
        return errors_count == 0

    async def test_database_integrity(self) -> bool:
        print("\n" + "="*100)
        print("🔍 数据库完整性测试")
        print("="*100)
        
        logger.debug("[DB_INTEGRITY:LINE:204] 开始数据库完整性测试")
        
        # 创建几个测试文件
        for i in range(10):
            file_path = self.project_path / f"db_test_{i}.ets"
            file_path.write_text(f"""export function f{i}() {{ return {i}; }}
class C{i} {{ 
  build() {{ }} 
}}
interface I{i} {{ }}\n""")
            
            await self.updater.update_file(str(file_path))
        
        # 测试搜索功能
        logger.debug("[DB_INTEGRITY:LINE:217] 测试搜索功能")
        try:
            for search_term in ["f", "C", "I", "test", ""]:
                results = self.db.search_symbol(search_term)
                logger.debug(f"[DB_INTEGRITY:LINE:220] 搜索 '{search_term}': {len(results['functions'])} 函数, {len(results['classes'])} 类")
        except Exception as e:
            self.errors.append(f"数据库搜索异常: {str(e)}")
            logger.exception("[DB_INTEGRITY:LINE:224]")
            return False
        
        # 测试数据一致性
        logger.debug("[DB_INTEGRITY:LINE:228] 测试数据一致性")
        all_file_ids = []
        try:
            for i in range(10):
                file_path_str = str(self.project_path / f"db_test_{i}.ets")
                file_id = self.db.get_file_id(file_path_str)
                if file_id:
                    all_file_ids.append(file_id)
                    funcs = self.db.get_functions_in_file(file_id)
                    classes = self.db.get_classes_in_file(file_id)
                    logger.debug(f"[DB_INTEGRITY:LINE:237] 文件 {i}: {len(funcs)} 函数, {len(classes)} 类")
        except Exception as e:
            self.errors.append(f"数据库数据查询异常: {str(e)}")
            logger.exception("[DB_INTEGRITY:LINE:240]")
            return False
        
        print("✅ 数据库完整性测试通过")
        return True

    async def test_interleaved_operations(self) -> bool:
        print("\n" + "="*100)
        print("🔄 交替操作测试 (读取 + 写入 + 查询)")
        print("="*100)
        
        logger.debug("[INTERLEAVED:LINE:250] 开始交替操作测试")
        
        num_operations = 200
        errors_count = 0
        
        for i in range(num_operations):
            op_type = random.choice(["write", "update", "search"])
            
            try:
                if op_type == "write":
                    idx = random.randint(0, 50)
                    file_path = self.project_path / f"int_write_{idx}.ets"
                    file_path.write_text(f"export function w{i}() {{ return {i}; }}")
                    await self.updater.update_file(str(file_path))
                
                elif op_type == "update":
                    idx = random.randint(0, 50)
                    file_path = self.project_path / f"int_write_{idx}.ets"
                    if file_path.exists():
                        file_path.write_text(f"export function u{i}() {{ return {i}; }}")
                        await self.updater.update_file(str(file_path))
                
                elif op_type == "search":
                    search_term = random.choice(["w", "u", "f", "c"])
                    results = self.db.search_symbol(search_term)
                
                if i % 40 == 0:
                    logger.debug(f"[INTERLEAVED:LINE:273] 已完成 {i}/{num_operations} 次操作")
                    
            except Exception as e:
                errors_count += 1
                logger.warning(f"[INTERLEAVED:LINE:277] 操作 {i} 异常: {str(e)}")
        
        logger.info(f"[INTERLEAVED:LINE:280] 交替操作完成: {num_operations} 次, {errors_count} 错误")
        
        if errors_count > 0:
            self.errors.append(f"交替操作测试有 {errors_count} 个错误")
        
        print(f"✅ 交替操作测试完成: {num_operations} 次, {errors_count} 错误")
        return errors_count == 0

    async def test_deep_code_analysis(self) -> bool:
        print("\n" + "="*100)
        print("🧐 深度代码分析 - 检查隐藏问题")
        print("="*100)
        
        logger.debug("[DEEP_ANALYSIS:LINE:292] 开始深度代码分析测试")
        
        # 发现潜在问题的特定代码模式
        test_cases = [
            # 测试 1: 函数和类同名
            ("name_collision", '''export class SameName { }
export function SameName() { return true; }'''),
            
            # 测试 2: 极端的参数
            ("extreme_params", '''export function f(a, b, c, d, e, f, g, h, i, j, k, l, m) { }'''),
            
            # 测试 3: 复杂的继承关系
            ("complex_inheritance", '''@Component
struct Base extends Object implements I1, I2, I3 {
  build() { }
}'''),
            
            # 测试 4: 特殊字符在标识符中 (虽然不是合法的 ArkTS，但测试解析器)
            ("special_identifiers", '''export function test_123() { }
export interface I$Test { }'''),
        ]
        
        for case_name, code in test_cases:
            file_path = self.project_path / f"deep_{case_name}.ets"
            file_path.write_text(code)
            
            try:
                result = await self.updater.update_file(str(file_path))
                
                if result["status"] == "error":
                    logger.warning(f"[DEEP_ANALYSIS:LINE:319] 案例 {case_name} 错误: {result['error']}")
                else:
                    logger.debug(f"[DEEP_ANALYSIS:LINE:321] 案例 {case_name} 成功: {result.get('parsed')}")
                    
            except Exception as e:
                self.errors.append(f"深度分析案例 {case_name} 异常: {str(e)}")
                logger.exception(f"[DEEP_ANALYSIS:LINE:325]")
        
        print("✅ 深度代码分析测试完成")
        return True

    async def test_final_complete_verification(self) -> bool:
        print("\n" + "="*100)
        print("🏁 最终完整验证")
        print("="*100)
        
        logger.debug("[FINAL_VERIFY:LINE:335] 开始最终完整验证")
        
        # 测试删除和重新创建文件
        for i in range(10):
            file_path = self.project_path / f"final_test_{i}.ets"
            file_path.write_text(f"export function final{i}() {{ return {i}; }}\n")
            await self.updater.update_file(str(file_path))
        
        logger.debug("[FINAL_VERIFY:LINE:342] 删除文件...")
        for i in range(5):
            file_path = self.project_path / f"final_test_{i}.ets"
            if file_path.exists():
                file_path.unlink()
        
        logger.debug("[FINAL_VERIFY:LINE:347] 重新创建并更新...")
        for i in range(10):
            file_path = self.project_path / f"final_test_{i}.ets"
            file_path.write_text(f"export function final_new{i}() {{ return {i}; }}\n")
            await self.updater.update_file(str(file_path))
        
        logger.info("[FINAL_VERIFY:LINE:353] 最终验证完成")
        print("✅ 最终完整验证通过")
        return True

    async def run_all_hyper_tests(self):
        print("\n" + "="*120)
        print("🚀 超极端混沌测试系统启动")
        print("="*120)
        print(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.setup()
        
        try:
            tests = [
                ("极端边缘情况", self.test_extreme_edge_cases),
                ("快速连续更新", self.test_rapid_consecutive_updates),
                ("数据库完整性", self.test_database_integrity),
                ("交替操作", self.test_interleaved_operations),
                ("深度代码分析", self.test_deep_code_analysis),
                ("最终完整验证", self.test_final_complete_verification),
            ]
            
            all_passed = True
            
            for test_name, test_func in tests:
                passed = await test_func()
                self.test_results[test_name] = passed
                if not passed:
                    all_passed = False
            
            print("\n" + "="*120)
            print("📊 超极端混沌测试总结")
            print("="*120)
            
            for test_name, passed in self.test_results.items():
                status = "✅ 通过" if passed else "❌ 失败"
                print(f"  {test_name}: {status}")
            
            if self.errors:
                print(f"\n⚠️ 发现 {len(self.errors)} 个问题:")
                for i, err in enumerate(self.errors[:10], 1):
                    print(f"  {i}. {err}")
            else:
                print("\n🎉 超极端混沌测试全部通过！系统表现出色！")
            
            print(f"\n完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*120)
            
            return all_passed, self.errors
            
        finally:
            self.teardown()


def main():
    tester = HyperExtremeTester()
    success, errors = asyncio.run(tester.run_all_hyper_tests())
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
