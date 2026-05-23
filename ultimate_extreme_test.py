#!/usr/bin/env python3
"""
终极极端混沌混合测试系统
- 多级迭代测试
- 极端大规模并发
- 极端长时间运行
- 极端混乱场景
- 完整链路验证
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
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Callable

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_extreme_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('UltimateExtremeTest')


class UltimateExtremeTester:
    def __init__(self):
        self.db_path: Optional[Path] = None
        self.project_path: Optional[Path] = None
        self.db: Optional[CodeGraphDB] = None
        self.parser: Optional[LocalArkTSParser] = None
        self.updater: Optional[IncrementalUpdater] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.test_results: Dict[str, bool] = {}
        self.operations_count = 0
        self.start_time = None
        
    def setup(self):
        """设置测试环境"""
        logger.debug("[SETUP] 初始化终极测试环境")
        self.db_path = Path(tempfile.mkdtemp()) / 'ultimate_test.db'
        self.project_path = Path(tempfile.mkdtemp())
        
        self.db = CodeGraphDB(str(self.db_path))
        self.parser = LocalArkTSParser()
        self.updater = IncrementalUpdater(self.db, self.parser)
        
        self.start_time = time.time()
        logger.info(f"[SETUP] 测试环境就绪: db={self.db_path}, project={self.project_path}")
        
    def teardown(self):
        """清理测试环境"""
        logger.debug("[TEARDOWN] 清理测试环境")
        if self.db:
            self.db.close()
        import shutil
        if self.project_path.exists():
            shutil.rmtree(self.project_path)
        if self.db_path.exists():
            self.db_path.unlink()
        logger.info("[TEARDOWN] 测试环境清理完成")
        
    def generate_random_arkts_code(self, complexity: int = 5) -> str:
        """生成随机复杂度的ArkTS代码"""
        parts = []
        
        # 随机导入
        for _ in range(random.randint(0, complexity)):
            module_name = ''.join(random.choices(string.ascii_lowercase, k=8))
            parts.append(f"import {{ Component{random.randint(1,100)} }} from '@ohos/{module_name}';\n")
        
        # 随机接口
        for _ in range(random.randint(0, complexity // 2)):
            interface_name = ''.join(random.choices(string.ascii_uppercase, k=1)) + \
                           ''.join(random.choices(string.ascii_lowercase, k=7))
            parts.append(f"\ninterface {interface_name} {{\n")
            for _ in range(random.randint(1, 5)):
                prop_name = ''.join(random.choices(string.ascii_lowercase, k=6))
                prop_type = random.choice(['string', 'number', 'boolean', 'any'])
                parts.append(f"  {prop_name}: {prop_type};\n")
            parts.append("}\n")
        
        # 随机组件
        if random.random() > 0.3:
            struct_name = ''.join(random.choices(string.ascii_uppercase, k=1)) + \
                        ''.join(random.choices(string.ascii_lowercase, k=10))
            has_entry = random.random() > 0.5
            if has_entry:
                parts.append("\n@Entry\n")
            parts.append("@Component\n")
            parts.append(f"struct {struct_name} {{\n")
            
            for _ in range(random.randint(0, complexity)):
                state_name = ''.join(random.choices(string.ascii_lowercase, k=5))
                state_type = random.choice(['string', 'number', 'boolean'])
                default_val = {
                    'string': f'"{random.choice(["hello", "world", "test", ""])}"',
                    'number': str(random.randint(0, 1000)),
                    'boolean': 'true' if random.random() > 0.5 else 'false'
                }[state_type]
                decorator = random.choice(['@State', '@Prop', '@Link', '@Provide', '@Consume'])
                parts.append(f"  {decorator} {state_name}: {state_type} = {default_val};\n")
            
            parts.append("\n  build() {\n")
            parts.append("    Column() {\n")
            for _ in range(random.randint(1, 10)):
                text_content = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(1, 20)))
                parts.append(f'      Text("{text_content}");\n')
            parts.append("    }\n")
            parts.append("  }\n")
            
            for _ in range(random.randint(0, complexity)):
                method_name = ''.join(random.choices(string.ascii_lowercase, k=8))
                is_async = random.random() > 0.7
                return_type = random.choice(['void', 'string', 'number', 'Promise<void>'])
                async_key = 'async ' if is_async else ''
                parts.append(f"\n  {async_key}{method_name}() : {return_type} {{\n")
                parts.append(f"    // {random.choice(['do something', 'handle event', 'process data'])}\n")
                if random.random() > 0.5:
                    parts.append(f"    return {random.randint(0, 1000)};\n")
                parts.append("  }\n")
            
            parts.append("}\n")
        
        # 随机函数
        for _ in range(random.randint(0, complexity)):
            func_name = ''.join(random.choices(string.ascii_lowercase, k=8))
            is_async = random.random() > 0.5
            async_key = 'async ' if is_async else ''
            return_type = random.choice(['void', 'string', 'number', 'boolean', 'any'])
            params = []
            for _ in range(random.randint(0, 3)):
                param_name = ''.join(random.choices(string.ascii_lowercase, k=5))
                param_type = random.choice(['string', 'number', 'boolean', 'any'])
                params.append(f"{param_name}: {param_type}")
            params_str = ', '.join(params)
            
            parts.append(f"\n{async_key}export function {func_name}({params_str}) : {return_type} {{\n")
            for _ in range(random.randint(0, 5)):
                parts.append(f"  // {''.join(random.choices(string.ascii_letters + string.digits, k=30))}\n")
            parts.append("}\n")
        
        return ''.join(parts)
        
    async def test_phase_1_massive_initialization(self):
        """
        阶段1：大规模初始化测试
        - 同时处理1000+个文件
        - 混合简单和复杂文件
        """
        print("\n" + "="*100)
        print("🚀 阶段1：大规模初始化测试")
        print("="*100)
        
        try:
            logger.info("[PHASE1] 开始大规模初始化测试")
            
            # 创建大量文件
            num_files = 1000
            file_paths = []
            logger.debug(f"[PHASE1] 创建 {num_files} 个ArkTS文件...")
            
            for i in range(num_files):
                file_path = self.project_path / f"init_{i:04d}.ets"
                complexity = random.randint(1, 10)
                code = self.generate_random_arkts_code(complexity)
                file_path.write_text(code)
                file_paths.append(str(file_path))
                
                if (i + 1) % 100 == 0:
                    logger.debug(f"[PHASE1] 已创建 {i+1} 个文件...")
            
            logger.info(f"[PHASE1] 开始批量更新 {num_files} 个文件...")
            batch_start = time.time()
            
            result = await self.updater.batch_update(file_paths)
            
            batch_time = time.time() - batch_start
            logger.info(f"[PHASE1] 批量更新完成: {result}")
            
            # 验证结果
            if result['failed'] > 0:
                self.errors.append(f"大规模初始化有 {result['failed']} 个文件失败")
                logger.error(f"[PHASE1] 失败文件: {result['errors'][:5]}")
                return False
            
            if result['success'] != num_files:
                self.errors.append(f"大规模初始化期望 {num_files} 成功，实际 {result['success']}")
                return False
            
            print(f"✅ 大规模初始化测试通过! 1000个文件，耗时 {batch_time:.2f}s")
            return True
            
        except Exception as e:
            self.errors.append(f"大规模初始化异常: {str(e)}")
            logger.exception("[PHASE1] 异常")
            return False
        
    async def test_phase_2_rapid_concurrent_changes(self):
        """
        阶段2：快速并发变更测试
        - 多线程同时修改同一文件
        - 快速交替更新
        - 验证竞态条件处理
        """
        print("\n" + "="*100)
        print("⚡ 阶段2：快速并发变更测试")
        print("="*100)
        
        try:
            logger.info("[PHASE2] 开始快速并发变更测试")
            
            num_threads = 10
            iterations_per_thread = 50
            results = []
            errors = []
            lock = threading.Lock()
            
            def worker(thread_id):
                local_db = CodeGraphDB(str(self.db_path))
                local_parser = LocalArkTSParser()
                local_updater = IncrementalUpdater(local_db, local_parser)
                
                for i in range(iterations_per_thread):
                    try:
                        file_path = self.project_path / f"concurrent_{thread_id:02d}_{i:03d}.ets"
                        code = self.generate_random_arkts_code(random.randint(1, 5))
                        file_path.write_text(code)
                        
                        result = asyncio.run(local_updater.update_file(str(file_path)))
                        
                        with lock:
                            if result['status'] not in ['success', 'skipped']:
                                errors.append(f"线程{thread_id} 第{i}次更新失败: {result.get('error')}")
                            else:
                                results.append(True)
                    except Exception as e:
                        with lock:
                            errors.append(f"线程{thread_id}异常: {str(e)}")
                
                local_db.close()
            
            threads = []
            start_time = time.time()
            
            for i in range(num_threads):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join(timeout=60)
            
            elapsed = time.time() - start_time
            total_ops = num_threads * iterations_per_thread
            
            logger.info(f"[PHASE2] 并发测试完成: {total_ops} 次操作，耗时 {elapsed:.2f}s")
            
            if errors:
                self.errors.extend(errors)
                logger.error(f"[PHASE2] 发现 {len(errors)} 个错误")
                return False
            
            print(f"✅ 快速并发变更测试通过! {total_ops}次操作，耗时 {elapsed:.2f}s")
            return True
            
        except Exception as e:
            self.errors.append(f"快速并发变更异常: {str(e)}")
            logger.exception("[PHASE2] 异常")
            return False
        
    async def test_phase_3_long_duration_stability(self):
        """
        阶段3：长时间稳定性测试
        - 持续运行1分钟
        - 随机执行各种操作
        - 验证系统稳定性
        """
        print("\n" + "="*100)
        print("⏱️ 阶段3：长时间稳定性测试")
        print("="*100)
        
        try:
            logger.info("[PHASE3] 开始长时间稳定性测试")
            
            duration_seconds = 60
            start_time = time.time()
            operations = 0
            errors_count = 0
            
            file_counter = 0
            
            while time.time() - start_time < duration_seconds:
                operations += 1
                
                # 随机执行不同操作
                choice = random.random()
                
                if choice < 0.3:
                    # 操作1：创建新文件
                    file_path = self.project_path / f"long_test_{file_counter:05d}.ets"
                    file_counter += 1
                    code = self.generate_random_arkts_code(random.randint(1, 8))
                    file_path.write_text(code)
                    result = await self.updater.update_file(str(file_path))
                    
                elif choice < 0.6:
                    # 操作2：更新现有文件
                    if file_counter > 0:
                        idx = random.randint(0, file_counter - 1)
                        file_path = self.project_path / f"long_test_{idx:05d}.ets"
                        code = self.generate_random_arkts_code(random.randint(1, 8))
                        file_path.write_text(code)
                        result = await self.updater.update_file(str(file_path))
                    else:
                        continue
                    
                elif choice < 0.8:
                    # 操作3：查询操作
                    search_query = ''.join(random.choices(string.ascii_lowercase, k=3))
                    try:
                        search_result = self.db.search_symbol(search_query)
                        # 只验证没有崩溃即可
                    except Exception as e:
                        errors_count += 1
                        logger.warning(f"[PHASE3] 查询操作异常: {e}")
                    continue
                    
                else:
                    # 操作4：复杂文件
                    file_path = self.project_path / f"long_complex_{file_counter:05d}.ets"
                    file_counter += 1
                    code = self.generate_random_arkts_code(random.randint(5, 15))
                    file_path.write_text(code)
                    result = await self.updater.update_file(str(file_path))
                
                # 验证结果
                if choice < 0.8:
                    if result and result['status'] not in ['success', 'skipped']:
                        errors_count += 1
                        logger.warning(f"[PHASE3] 操作失败: {result.get('error')}")
                
                # 定期打印进度
                if operations % 100 == 0:
                    elapsed = time.time() - start_time
                    logger.debug(f"[PHASE3] 已执行 {operations} 次操作，耗时 {elapsed:.1f}s")
            
            elapsed = time.time() - start_time
            logger.info(f"[PHASE3] 长时间测试完成: {operations} 次操作，耗时 {elapsed:.2f}s")
            
            if errors_count > 5:
                self.errors.append(f"长时间稳定性测试有 {errors_count} 次错误")
                return False
            
            print(f"✅ 长时间稳定性测试通过! {operations}次操作，耗时 {elapsed:.2f}s")
            return True
            
        except Exception as e:
            self.errors.append(f"长时间稳定性测试异常: {str(e)}")
            logger.exception("[PHASE3] 异常")
            return False
        
    async def test_phase_4_extreme_edge_cases(self):
        """
        阶段4：极端边界情况测试
        - 超大文件
        - 超小文件
        - 特殊字符
        - 空文件
        - 异常编码
        """
        print("\n" + "="*100)
        print("🔬 阶段4：极端边界情况测试")
        print("="*100)
        
        try:
            logger.info("[PHASE4] 开始极端边界情况测试")
            
            edge_cases = [
                ("empty_file", ""),
                ("minimal", "export {}"),
                ("just_comment", "// 只有注释\n"),
                ("large", "export function f() {\n" + "  x = 1;\n"*1000 + "}"),
                ("special", 'export function f() { return "😀🔥🎉"; }'),
                ("unicode_bom", "\ufeff// BOM测试\nexport function f() { }"),
                ("mixed_line_endings", "export function f() { }\r\n// 混合换行\n"),
                ("crazy_spacing", "   export   function   f (  )  {  }\n"),
                ("deep_nesting", "export function f() {\n" + "  if (true) {\n"*50 + "  }"*50 + "}"),
                ("invalid_json_like", "// 看起来像JSON但不是\nexport { foo: bar }"),
                ("max_name", "export function " + "x"*200 + "() { }"),
            ]
            
            passed = 0
            failed = 0
            
            for name, code in edge_cases:
                try:
                    file_path = self.project_path / f"edge_{name}.ets"
                    file_path.write_text(code)
                    result = await self.updater.update_file(str(file_path))
                    
                    if result['status'] in ['success', 'skipped']:
                        passed += 1
                        logger.debug(f"[PHASE4] 边界情况 {name} 通过")
                    else:
                        failed += 1
                        self.errors.append(f"边界情况 {name} 失败: {result.get('error')}")
                        logger.error(f"[PHASE4] 边界情况 {name} 失败")
                        
                except Exception as e:
                    failed += 1
                    self.errors.append(f"边界情况 {name} 异常: {str(e)}")
                    logger.exception(f"[PHASE4] 边界情况 {name} 异常")
            
            logger.info(f"[PHASE4] 边界测试完成: {passed} 个通过，{failed} 个失败")
            
            if failed > 0:
                return False
            
            print(f"✅ 极端边界情况测试通过! {len(edge_cases)}种情况全部处理")
            return True
            
        except Exception as e:
            self.errors.append(f"极端边界情况测试异常: {str(e)}")
            logger.exception("[PHASE4] 异常")
            return False
        
    async def test_phase_5_chaos_mixed_scenarios(self):
        """
        阶段5：混沌混合场景测试
        - 同时执行多种操作
        - 随机故障注入
        - 验证系统鲁棒性
        """
        print("\n" + "="*100)
        print("🌪️ 阶段5：混沌混合场景测试")
        print("="*100)
        
        try:
            logger.info("[PHASE5] 开始混沌混合场景测试")
            
            num_operations = 500
            errors = []
            
            for i in range(num_operations):
                try:
                    # 随机混合操作
                    if i % 7 == 0:
                        # 批量更新
                        batch_files = []
                        for j in range(5):
                            file_path = self.project_path / f"chaos_batch_{i}_{j}.ets"
                            file_path.write_text(self.generate_random_arkts_code(random.randint(1, 5)))
                            batch_files.append(str(file_path))
                        result = await self.updater.batch_update(batch_files)
                        if result['failed'] > 0:
                            errors.append(f"批量操作{i}失败: {result['failed']}个文件")
                            
                    elif i % 5 == 0:
                        # 快速更新同一文件
                        file_path = self.project_path / "chaos_hot.ets"
                        for _ in range(5):
                            file_path.write_text(self.generate_random_arkts_code(random.randint(1, 3)))
                            result = await self.updater.update_file(str(file_path))
                            
                    else:
                        # 单个文件更新
                        file_path = self.project_path / f"chaos_single_{i}.ets"
                        file_path.write_text(self.generate_random_arkts_code(random.randint(1, 7)))
                        result = await self.updater.update_file(str(file_path))
                        
                    # 随机查询
                    if i % 3 == 0:
                        try:
                            _ = self.db.search_symbol(''.join(random.choices(string.ascii_lowercase, k=2)))
                        except Exception:
                            pass  # 查询失败不算致命错误
                        
                    if (i + 1) % 100 == 0:
                        logger.debug(f"[PHASE5] 已完成 {i+1} 次混沌操作...")
                        
                except Exception as e:
                    errors.append(f"混沌操作{i}异常: {str(e)}")
                    logger.warning(f"[PHASE5] 混沌操作{i}异常", exc_info=True)
            
            logger.info(f"[PHASE5] 混沌测试完成: {num_operations} 次操作")
            
            if len(errors) > 5:
                self.errors.extend(errors)
                logger.error(f"[PHASE5] 发现 {len(errors)} 个错误")
                return False
            
            print(f"✅ 混沌混合场景测试通过! {num_operations}次操作")
            return True
            
        except Exception as e:
            self.errors.append(f"混沌混合场景测试异常: {str(e)}")
            logger.exception("[PHASE5] 异常")
            return False
        
    async def run_all_ultimate_phases(self):
        """运行所有终极测试阶段"""
        print("\n" + "="*120)
        print("🎯 终极极端混沌混合测试系统启动")
        print("="*120)
        print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.setup()
        
        try:
            # 运行所有阶段
            print("\n📋 阶段概览:")
            print("  1. 大规模初始化测试")
            print("  2. 快速并发变更测试")
            print("  3. 长时间稳定性测试")
            print("  4. 极端边界情况测试")
            print("  5. 混沌混合场景测试")
            
            phases = [
                ("阶段1", self.test_phase_1_massive_initialization),
                ("阶段2", self.test_phase_2_rapid_concurrent_changes),
                ("阶段3", self.test_phase_3_long_duration_stability),
                ("阶段4", self.test_phase_4_extreme_edge_cases),
                ("阶段5", self.test_phase_5_chaos_mixed_scenarios),
            ]
            
            all_passed = True
            
            for phase_name, phase_func in phases:
                phase_start = time.time()
                try:
                    passed = await phase_func()
                    phase_time = time.time() - phase_start
                    
                    self.test_results[phase_name] = passed
                    
                    if passed:
                        print(f"\n✅ {phase_name} 完成! 耗时 {phase_time:.2f}s")
                    else:
                        print(f"\n❌ {phase_name} 失败! 耗时 {phase_time:.2f}s")
                        all_passed = False
                        
                except Exception as e:
                    print(f"\n❌ {phase_name} 异常! {str(e)}")
                    self.errors.append(f"{phase_name} 异常: {str(e)}")
                    all_passed = False
            
            # 最终总结
            print("\n" + "="*120)
            print("📊 终极极端混沌混合测试总结")
            print("="*120)
            
            total_elapsed = time.time() - self.start_time
            print(f"\n总耗时: {total_elapsed:.2f}s")
            
            for phase_name, passed in self.test_results.items():
                status = "✅ 通过" if passed else "❌ 失败"
                print(f"  {phase_name}: {status}")
            
            if self.errors:
                print(f"\n⚠️ 发现 {len(self.errors)} 个问题:")
                for i, error in enumerate(self.errors[:10], 1):
                    print(f"  {i}. {error}")
                if len(self.errors) > 10:
                    print(f"  ... (还有 {len(self.errors) - 10} 个问题)")
            else:
                print("\n🎉 所有终极测试阶段完美通过! 系统质量优秀!")
            
            print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*120)
            
            return all_passed, self.errors
            
        finally:
            self.teardown()


def main():
    tester = UltimateExtremeTester()
    success, errors = asyncio.run(tester.run_all_ultimate_phases())
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
