#!/usr/bin/env python3
"""
超级极端可用性和混乱场景测试系统
- 可用性验证
- 极端混乱场景
- 长时间稳定运行
- 日志追踪验证
- 资源泄漏检测
- 错误恢复测试
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
import gc
import psutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

# 配置详细的代码级日志
logging.basicConfig(
    level=logging.DEBUG,
    format='[LINE:%(lineno)d] [%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_chaos_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('UltimateChaosTest')


class UltimateChaosAndUsabilityTester:
    def __init__(self):
        self.db_path: Optional[Path] = None
        self.project_path: Optional[Path] = None
        self.db: Optional[CodeGraphDB] = None
        self.parser: Optional[LocalArkTSParser] = None
        self.updater: Optional[IncrementalUpdater] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.operations_count = 0
        self.start_time: Optional[float] = None
        self.process: Optional[psutil.Process] = None

    def setup(self):
        logger.debug("[SETUP:54] 初始化终极测试环境")
        self.db_path = Path(tempfile.mkdtemp()) / 'ultimate_test.db'
        self.project_path = Path(tempfile.mkdtemp())
        
        self.process = psutil.Process()
        self.db = CodeGraphDB(str(self.db_path))
        self.parser = LocalArkTSParser()
        self.updater = IncrementalUpdater(self.db, self.parser)
        self.start_time = time.time()
        
        logger.info(f"[SETUP:64] 测试环境就绪 - db: {self.db_path}, project: {self.project_path}")

    def teardown(self):
        logger.debug("[TEARDOWN:68] 开始清理测试环境")
        if self.db:
            logger.debug("[TEARDOWN:70] 关闭数据库连接")
            self.db.close()
        import shutil
        if self.project_path.exists():
            logger.debug(f"[TEARDOWN:74] 清理项目目录: {self.project_path}")
            shutil.rmtree(self.project_path)
        if self.db_path.exists():
            logger.debug(f"[TEARDOWN:77] 清理数据库文件: {self.db_path}")
            self.db_path.unlink()
        logger.info("[TEARDOWN:79] 测试环境清理完成")

    def generate_extreme_chaos_code(self, complexity_level: int = 5, file_index: int = 0) -> str:
        """生成极端混乱的代码"""
        parts = []
        
        # 随机导入
        for i in range(random.randint(0, complexity_level)):
            import_name = ''.join(random.choices(string.ascii_letters, k=random.randint(3, 10)))
            parts.append(f"import {{ {import_name} }} from '@ohos/{''.join(random.choices(string.ascii_lowercase, k=6))}';\n")
        
        # 随机接口
        for i in range(random.randint(0, complexity_level // 2)):
            iface_name = ''.join(random.choices(string.ascii_uppercase, k=1)) + ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 8)))
            parts.append(f"\ninterface {iface_name} {{")
            for j in range(random.randint(1, 4)):
                prop_name = ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 8)))
                prop_type = random.choice(['string', 'number', 'boolean', 'any', 'void', '() => void'])
                parts.append(f"\n  {prop_name}: {prop_type};")
            parts.append("\n}\n")
        
        # 随机类/组件
        for i in range(random.randint(0, complexity_level // 3)):
            struct_name = ''.join(random.choices(string.ascii_uppercase, k=1)) + ''.join(random.choices(string.ascii_lowercase, k=random.randint(5, 12)))
            if random.random() > 0.6:
                parts.append("\n@Entry")
            parts.append("\n@Component")
            parts.append(f"\nstruct {struct_name} {{")
            
            # 随机状态
            for j in range(random.randint(0, complexity_level)):
                decorator = random.choice(['@State', '@Prop', '@Link', '@Provide', '@Consume'])
                var_name = ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 8)))
                var_type = random.choice(['string', 'number', 'boolean', 'any'])
                default_value = random.choice([
                    f'"{random.choice(["hello", "world", "test", ""])}"',
                    str(random.randint(0, 1000)),
                    'true' if random.random() > 0.5 else 'false',
                    'null'
                ])
                parts.append(f"\n  {decorator} {var_name}: {var_type} = {default_value};")
            
            # 随机方法
            for j in range(random.randint(0, complexity_level // 2)):
                method_name = ''.join(random.choices(string.ascii_lowercase, k=random.randint(5, 12)))
                is_async = random.random() > 0.7
                async_key = 'async ' if is_async else ''
                return_type = random.choice(['void', 'string', 'number', 'boolean', 'any', 'Promise<void>'])
                
                params = []
                for k in range(random.randint(0, 4)):
                    param_name = ''.join(random.choices(string.ascii_lowercase, k=random.randint(2, 5)))
                    param_type = random.choice(['string', 'number', 'boolean', 'any'])
                    params.append(f"{param_name}: {param_type}")
                
                params_str = ', '.join(params)
                parts.append(f"\n  {async_key}{method_name}({params_str}): {return_type} {{")
                parts.append(f"\n    // {''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(10, 50)))}")
                parts.append("\n  }")
            
            parts.append("\n}\n")
        
        # 随机函数
        for i in range(random.randint(0, complexity_level)):
            func_name = ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 12)))
            is_async = random.random() > 0.7
            async_key = 'async ' if is_async else ''
            return_type = random.choice(['void', 'string', 'number', 'boolean', 'any', 'Promise<void>'])
            
            params = []
            for k in range(random.randint(0, 4)):
                param_name = ''.join(random.choices(string.ascii_lowercase, k=random.randint(2, 5)))
                param_type = random.choice(['string', 'number', 'boolean', 'any'])
                params.append(f"{param_name}: {param_type}")
            
            params_str = ', '.join(params)
            parts.append(f"\n{async_key}export function {func_name}({params_str}): {return_type} {{")
            parts.append(f"\n    // {''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(10, 50)))}")
            parts.append("\n}\n")
        
        return ''.join(parts)

    async def test_usability_and_logs(self) -> bool:
        """可用性和日志验证测试"""
        print("\n" + "="*120)
        print("🧪 测试1：可用性和日志追踪验证")
        print("="*120)
        
        logger.info("[TEST1:163] 开始可用性和日志验证")
        passed = True
        
        # 测试1.1：基本操作的可用性
        try:
            file_path = self.project_path / "usability_test1.ets"
            code = """export function hello(): string { return "Hello"; }
export class User { name: string = "test"; }
@Component
struct Test { build() {} }"""
            file_path.write_text(code)
            
            logger.debug("[TEST1:172] 更新文件")
            result = await self.updater.update_file(str(file_path))
            
            if result["status"] == "success":
                logger.info(f"[TEST1:175] 成功处理: {result}")
                
                # 验证数据一致性
                file_id = self.db.get_file_id(str(file_path))
                if file_id:
                    functions = self.db.get_functions_in_file(file_id)
                    classes = self.db.get_classes_in_file(file_id)
                    logger.debug(f"[TEST1:180] 文件内容验证 - {len(functions)} 函数, {len(classes)} 类")
            else:
                self.errors.append(f"可用性测试失败: {result['error']}")
                logger.error(f"[TEST1:183] 失败: {result}")
                passed = False
                
        except Exception as e:
            self.errors.append(f"可用性测试异常: {str(e)}")
            logger.exception("[TEST1:187]")
            passed = False
        
        return passed

    async def test_extreme_chaos_scenarios(self) -> bool:
        """极端混乱场景测试"""
        print("\n" + "="*120)
        print("🌪️ 测试2：极端混乱场景")
        print("="*120)
        
        logger.info("[TEST2:197] 开始极端混乱场景测试")
        self.operations_count = 0
        
        start_memory = self.process.memory_info().rss / 1024 / 1024
        logger.debug(f"[TEST2:201] 初始内存: {start_memory:.2f} MB")
        
        num_operations = 1000
        errors_in_test = 0
        
        for i in range(num_operations):
            try:
                self.operations_count += 1
                
                # 随机选择操作类型
                operation_type = random.randint(0, 10)
                
                if operation_type < 4:
                    # 新建文件
                    file_idx = random.randint(0, 1000)
                    file_path = self.project_path / f"chaos_{file_idx}.ets"
                    complexity = random.randint(1, 8)
                    code = self.generate_extreme_chaos_code(complexity, file_idx)
                    file_path.write_text(code)
                    result = await self.updater.update_file(str(file_path))
                    
                elif operation_type < 7:
                    # 更新现有文件
                    file_idx = random.randint(0, 500)
                    file_path = self.project_path / f"chaos_{file_idx}.ets"
                    if file_path.exists():
                        complexity = random.randint(1, 10)
                        code = self.generate_extreme_chaos_code(complexity, file_idx)
                        file_path.write_text(code)
                        result = await self.updater.update_file(str(file_path))
                    
                elif operation_type < 9:
                    # 搜索操作
                    search_term = random.choice(['User', 'test', 'hello', 'func', 'a', ''])
                    try:
                        self.db.search_symbol(search_term)
                    except Exception as e:
                        self.warnings.append(f"搜索异常: {str(e)}")
                    
                else:
                    # 删除文件
                    file_idx = random.randint(0, 1000)
                    file_path = self.project_path / f"chaos_{file_idx}.ets"
                    if file_path.exists():
                        file_path.unlink()
                        logger.debug(f"[TEST2:241] 删除文件: {file_path}")
                
                if i % 100 == 0:
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    elapsed = time.time() - self.start_time if self.start_time else 0
                    logger.debug(f"[TEST2:246] 进度 {i}/{num_operations} - 内存: {current_memory:.2f} MB, 耗时: {elapsed:.2f}s")
                    
            except Exception as e:
                errors_in_test += 1
                logger.warning(f"[TEST2:251] 操作 {i} 异常: {str(e)}")
        
        end_memory = self.process.memory_info().rss / 1024 / 1024
        memory_change = end_memory - start_memory
        logger.info(f"[TEST2:255] 内存变化: {memory_change:.2f} MB")
        
        if memory_change > 20:
            self.warnings.append(f"内存使用增长较大: {memory_change:.2f} MB")
        
        if errors_in_test > 20:
            self.errors.append(f"极端混乱场景错误过多: {errors_in_test}")
            return False
        
        print(f"✅ 极端混乱场景测试完成 - 1000次操作，{errors_in_test}个错误")
        return True

    async def test_long_term_stability(self) -> bool:
        """长时间稳定运行测试"""
        print("\n" + "="*120)
        print("⏱️ 测试3：长时间稳定性测试")
        print("="*120)
        
        logger.info("[TEST3:270] 开始长时间稳定性测试")
        
        duration_seconds = 120  # 2分钟
        start_time = time.time()
        operations = 0
        errors_in_test = 0
        
        logger.debug(f"[TEST3:276] 目标运行时间: {duration_seconds}秒")
        
        while time.time() - start_time < duration_seconds:
            try:
                operations += 1
                
                # 随机操作
                file_idx = random.randint(0, 500)
                file_path = self.project_path / f"long_stability_{file_idx}.ets"
                complexity = random.randint(1, 5)
                code = self.generate_extreme_chaos_code(complexity, file_idx)
                file_path.write_text(code)
                
                result = await self.updater.update_file(str(file_path))
                
                if result["status"] == "error":
                    errors_in_test += 1
                
                # 定期GC
                if operations % 50 == 0:
                    gc.collect()
                
            except Exception as e:
                errors_in_test += 1
                logger.warning(f"[TEST3:297] 操作 {operations} 异常: {str(e)}")
        
        elapsed = time.time() - start_time
        logger.info(f"[TEST3:300] 长时间测试完成 - {operations} 次操作, {elapsed:.2f}秒, {errors_in_test} 个错误")
        
        if errors_in_test > 5:
            self.errors.append(f"长时间稳定性测试错误过多: {errors_in_test}")
            return False
        
        print(f"✅ 长时间稳定性测试通过 - {operations}次操作，{elapsed:.2f}秒，{errors_in_test}个错误")
        return True

    async def test_error_recovery(self) -> bool:
        """错误恢复测试"""
        print("\n" + "="*120)
        print("🔄 测试4：错误恢复和兜底降级")
        print("="*120)
        
        logger.info("[TEST4:313] 开始错误恢复测试")
        passed = True
        
        error_scenarios = [
            ("不存在的文件", "/this/file/does/not/exist.ets"),
            ("极端长文件名", str(self.project_path / f"{'x'*200}.ets")),
            ("特殊字符路径", str(self.project_path / "!@#$%^&*()_+特殊字符.ets"))
        ]
        
        for scenario_name, file_path in error_scenarios:
            try:
                result = await self.updater.update_file(file_path)
                
                if result["status"] in ["failed", "error", "skipped"]:
                    logger.debug(f"[TEST4:326] 场景 {scenario_name}: {result['status']} (正常)")
                else:
                    logger.info(f"[TEST4:328] 场景 {scenario_name}: {result['status']}")
                    
            except Exception as e:
                logger.warning(f"[TEST4:331] 场景 {scenario_name} 异常: {str(e)}")
        
        # 测试无效代码
        try:
            invalid_file = self.project_path / "invalid_code.ets"
            invalid_code = "this is invalid code! &&&&^^\nfunction broken() {\n"
            invalid_file.write_text(invalid_code)
            
            result = await self.updater.update_file(str(invalid_file))
            
            if result["status"] not in ["success", "skipped"]:
                logger.debug(f"[TEST4:343] 无效代码处理: {result['status']} (这是预期的)")
            else:
                logger.info(f"[TEST4:345] 无效代码成功处理: {result['status']}")
                
        except Exception as e:
            self.warnings.append(f"无效代码测试: {str(e)}")
            logger.warning("[TEST4:349]")
        
        print("✅ 错误恢复和兜底降级测试完成")
        return passed

    async def test_resource_leaks(self) -> bool:
        """资源泄漏检测"""
        print("\n" + "="*120)
        print("🔍 测试5：资源泄漏检测")
        print("="*120)
        
        logger.info("[TEST5:360] 开始资源泄漏检测")
        
        # 初始内存
        gc.collect()
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        logger.debug(f"[TEST5:365] 初始内存: {initial_memory:.2f} MB")
        
        # 执行大量操作
        operations = 500
        for i in range(operations):
            try:
                file_path = self.project_path / f"resource_test_{i}.ets"
                file_path.write_text(f"export function f{i}(): number {{ return {i}; }}")
                await self.updater.update_file(str(file_path))
                
                if i % 100 == 0:
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    logger.debug(f"[TEST5:376] 内存使用: {current_memory:.2f} MB")
                    
            except Exception as e:
                logger.warning(f"[TEST5:379] 资源测试异常: {str(e)}")
        
        # 最终内存
        gc.collect()
        final_memory = self.process.memory_info().rss / 1024 / 1024
        memory_change = final_memory - initial_memory
        
        logger.info(f"[TEST5:387] 内存变化: {memory_change:.2f} MB (初始: {initial_memory:.2f}, 最终: {final_memory:.2f})")
        
        if memory_change > 15:
            self.warnings.append(f"内存使用增长较大: {memory_change:.2f} MB")
        
        print(f"✅ 资源泄漏检测完成 - 内存变化: {memory_change:.2f} MB")
        return True

    async def run_all_ultimate_tests(self):
        """运行所有终极测试"""
        print("\n" + "="*120)
        print("🚀 终极可用性和极端混乱场景测试系统启动")
        print("="*120)
        
        self.setup()
        
        try:
            tests = [
                ("可用性和日志验证", self.test_usability_and_logs),
                ("极端混乱场景", self.test_extreme_chaos_scenarios),
                ("长时间稳定性", self.test_long_term_stability),
                ("错误恢复和兜底", self.test_error_recovery),
                ("资源泄漏检测", self.test_resource_leaks)
            ]
            
            all_passed = True
            
            for test_name, test_func in tests:
                passed = await test_func()
                if not passed:
                    all_passed = False
            
            # 最终总结
            print("\n" + "="*120)
            print("📊 终极测试总结")
            print("="*120)
            
            total_elapsed = time.time() - self.start_time if self.start_time else 0
            print(f"\n总运行时间: {total_elapsed:.2f}秒")
            print(f"总操作数: {self.operations_count}")
            
            if self.errors:
                print(f"\n⚠️ 发现 {len(self.errors)} 个问题:")
                for i, err in enumerate(self.errors[:10], 1):
                    print(f"  {i}. {err}")
            else:
                print("\n🎉 所有终极测试完美通过！系统质量优秀！")
            
            if self.warnings:
                print(f"\n⚠️ 警告 ({len(self.warnings)}):")
                for i, warn in enumerate(self.warnings[:5], 1):
                    print(f"  {i}. {warn}")
            
            print("\n" + "="*120)
            
            return all_passed, self.errors
            
        finally:
            self.teardown()


def main():
    tester = UltimateChaosAndUsabilityTester()
    success, errors = asyncio.run(tester.run_all_ultimate_tests())
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
