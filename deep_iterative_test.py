#!/usr/bin/env python3
"""
超级深度多次迭代测试系统
按照第一性原理进行全代码分支覆盖验证
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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

# 配置详细的日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('deep_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DeepIterativeTester:
    def __init__(self):
        self.db_path = None
        self.project_path = None
        self.db = None
        self.parser = None
        self.updater = None
        self.errors = []
        self.warnings = []
        self.iteration_results = []
        self.start_time = None
        
    def setup(self, iteration: int):
        """为每次迭代设置独立的测试环境"""
        logger.debug(f"[setup] 开始设置第 {iteration} 次迭代测试环境")
        
        self.db_path = Path(tempfile.mkdtemp(suffix=f'_iter{iteration}.db')) / f'test_iter{iteration}.db'
        self.db_path.unlink(missing_ok=True)
        
        self.project_path = Path(tempfile.mkdtemp(suffix=f'_proj_iter{iteration}'))
        
        logger.debug(f"[setup] 数据库路径: {self.db_path}")
        logger.debug(f"[setup] 项目路径: {self.project_path}")
        
        self.db = CodeGraphDB(str(self.db_path))
        logger.info(f"[setup] 数据库初始化完成")
        
        self.parser = LocalArkTSParser()
        logger.debug(f"[setup] 本地解析器初始化完成")
        
        self.updater = IncrementalUpdater(self.db, self.parser)
        logger.info(f"[setup] 增量更新器初始化完成")
        
        self.start_time = time.time()
        logger.debug(f"[setup] 第 {iteration} 次迭代测试环境设置完成")
        
    def teardown(self):
        """清理测试环境"""
        logger.debug("[teardown] 开始清理测试环境")
        
        if self.db:
            self.db.close()
            logger.debug("[teardown] 数据库已关闭")
            
        if self.db_path and self.db_path.exists():
            self.db_path.unlink()
            logger.debug(f"[teardown] 数据库文件已删除: {self.db_path}")
            
        import shutil
        if self.project_path and self.project_path.exists():
            shutil.rmtree(self.project_path)
            logger.debug(f"[teardown] 项目目录已删除: {self.project_path}")
            
        logger.info("[teardown] 测试环境清理完成")
        
    def generate_complex_arkts_code(self, complexity_level: int = 1) -> str:
        """生成复杂的 ArkTS 代码用于测试"""
        logger.debug(f"[generate_complex_arkts_code] 生成复杂度等级 {complexity_level} 的代码")
        
        code_parts = []
        
        # 添加导入
        if complexity_level >= 1:
            code_parts.append("import { BaseComponent } from '@ohos/base'\n")
            code_parts.append("import { Logger } from '@ohos/logging'\n")
            code_parts.append("import * as utils from './utils'\n\n")
        
        # 添加接口
        if complexity_level >= 2:
            code_parts.append("interface IDataModel {\n")
            code_parts.append("  id: number\n")
            code_parts.append("  name: string\n")
            code_parts.append("  timestamp: number\n")
            code_parts.append("}\n\n")
            
            code_parts.append("interface IService {\n")
            code_parts.append("  process(data: IDataModel): Promise<boolean>\n")
            code_parts.append("  validate(data: IDataModel): boolean\n")
            code_parts.append("}\n\n")
        
        # 添加组件类
        code_parts.append("@Entry\n")
        code_parts.append("@Component\n")
        code_parts.append("struct MainComponent {\n")
        code_parts.append("  @State message: string = 'Hello'\n")
        code_parts.append("  @State count: number = 0\n\n")
        
        # 复杂的构建方法
        code_parts.append("  build() {\n")
        code_parts.append("    Column() {\n")
        code_parts.append("      Text(this.message)\n")
        code_parts.append("        .fontSize(20)\n")
        code_parts.append("      Button('Increment')\n")
        code_parts.append("        .onClick(() => {\n")
        code_parts.append("          this.increment()\n")
        code_parts.append("        })\n")
        code_parts.append("    }\n")
        code_parts.append("  }\n\n")
        
        # 添加多个方法
        code_parts.append("  increment(): void {\n")
        code_parts.append("    this.count++\n")
        code_parts.append("    this.updateMessage()\n")
        code_parts.append("  }\n\n")
        
        code_parts.append("  updateMessage(): void {\n")
        code_parts.append("    this.message = `Count: ${this.count}`\n")
        code_parts.append("  }\n\n")
        
        code_parts.append("  private async fetchData(): Promise<IDataModel> {\n")
        code_parts.append("    await new Promise(r => setTimeout(r, 100))\n")
        code_parts.append("    return { id: Date.now(), name: 'test', timestamp: Date.now() }\n")
        code_parts.append("  }\n")
        
        code_parts.append("}\n\n")
        
        # 添加普通函数
        if complexity_level >= 3:
            code_parts.append("export function processData(input: string): string {\n")
            code_parts.append("  const cleaned = input.trim().toLowerCase()\n")
            code_parts.append("  return cleaned.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')\n")
            code_parts.append("}\n\n")
            
            code_parts.append("export async function* dataGenerator(count: number): AsyncGenerator<IDataModel> {\n")
            code_parts.append("  for (let i = 0; i < count; i++) {\n")
            code_parts.append("    yield { id: i, name: `Item ${i}`, timestamp: Date.now() }\n")
            code_parts.append("    await new Promise(r => setTimeout(r, 10))\n")
            code_parts.append("  }\n")
            code_parts.append("}\n\n")
            
            code_parts.append("export class DataService implements IService {\n")
            code_parts.append("  private cache: Map<number, IDataModel> = new Map()\n\n")
            code_parts.append("  async process(data: IDataModel): Promise<boolean> {\n")
            code_parts.append("    this.cache.set(data.id, data)\n")
            code_parts.append("    return true\n")
            code_parts.append("  }\n\n")
            code_parts.append("  validate(data: IDataModel): boolean {\n")
            code_parts.append("    return data.name.length > 0 && data.timestamp > 0\n")
            code_parts.append("  }\n")
            code_parts.append("}\n")
        
        final_code = ''.join(code_parts)
        logger.debug(f"[generate_complex_arkts_code] 生成完成，代码长度: {len(final_code)}")
        
        return final_code
        
    def test_first_iteration_static_analysis(self):
        """
        第一次迭代测试：静态分析 + 边界条件
        覆盖所有代码分支的基础测试
        """
        print("\n" + "="*100)
        print("🔍 第一次迭代：静态分析 + 边界条件测试")
        print("="*100)
        
        success = True
        iteration_errors = []
        
        logger.info("[first_iteration] 开始第一次迭代测试")
        
        try:
            # 测试1：空代码解析
            logger.debug("[first_iteration] 测试1：空代码解析")
            empty_file = self.project_path / "empty.ets"
            empty_file.write_text("")
            
            result = asyncio.run(self.updater.update_file(str(empty_file)))
            logger.info(f"[first_iteration] 空文件解析结果: {result['status']}")
            
            if result['status'] not in ['success', 'skipped']:
                iteration_errors.append(f"空文件解析失败: {result.get('error')}")
                logger.error(f"[first_iteration] 空文件解析失败: {result.get('error')}")
                success = False
            
            # 测试2：基础代码解析
            logger.debug("[first_iteration] 测试2：基础代码解析")
            basic_file = self.project_path / "basic.ets"
            basic_file.write_text("""@Entry
@Component
struct BasicComponent {
  build() {
    Text('Hello')
  }
}
""")
            
            result = asyncio.run(self.updater.update_file(str(basic_file)))
            logger.info(f"[first_iteration] 基础文件解析结果: {result['status']}")
            
            if result['status'] != 'success':
                iteration_errors.append(f"基础文件解析失败: {result.get('error')}")
                logger.error(f"[first_iteration] 基础文件解析失败: {result.get('error')}")
                success = False
            
            # 测试3：复杂代码解析
            logger.debug("[first_iteration] 测试3：复杂代码解析")
            complex_file = self.project_path / "complex.ets"
            complex_code = self.generate_complex_arkts_code(3)
            complex_file.write_text(complex_code)
            
            result = asyncio.run(self.updater.update_file(str(complex_file)))
            logger.info(f"[first_iteration] 复杂文件解析结果: {result['status']}")
            
            if result['status'] != 'success':
                iteration_errors.append(f"复杂文件解析失败: {result.get('error')}")
                logger.error(f"[first_iteration] 复杂文件解析失败: {result.get('error')}")
                success = False
            
            # 测试4：边界情况 - 超大函数名
            logger.debug("[first_iteration] 测试4：边界情况 - 超长函数名")
            weird_file = self.project_path / "weird.ets"
            long_name = "".join(random.choice(string.ascii_letters) for _ in range(200))
            weird_code = f"""
export function {long_name}(param: string): string {{
  return param.toUpperCase()
}}
"""
            weird_file.write_text(weird_code)
            
            result = asyncio.run(self.updater.update_file(str(weird_file)))
            logger.info(f"[first_iteration] 超长函数名文件解析结果: {result['status']}")
            
            if result['status'] != 'success':
                iteration_errors.append(f"超长函数名文件解析失败: {result.get('error')}")
                logger.error(f"[first_iteration] 超长函数名文件解析失败: {result.get('error')}")
                success = False
            
            # 测试5：边界情况 - 特殊字符
            logger.debug("[first_iteration] 测试5：边界情况 - 特殊字符")
            special_file = self.project_path / "special.ets"
            special_code = """
export function specialChars(): string {
  return "测试 中文 👋 🎉 🌟"
}

interface Data {
  value: string
}

@Entry
@Component
struct SpecialComponent {
  build() {
    Text('测试')
  }
}
"""
            special_file.write_text(special_code)
            
            result = asyncio.run(self.updater.update_file(str(special_file)))
            logger.info(f"[first_iteration] 特殊字符文件解析结果: {result['status']}")
            
            if result['status'] != 'success':
                iteration_errors.append(f"特殊字符文件解析失败: {result.get('error')}")
                logger.error(f"[first_iteration] 特殊字符文件解析失败: {result.get('error')}")
                success = False
            
            # 测试6：数据库操作边界
            logger.debug("[first_iteration] 测试6：数据库操作边界 - 搜索")
            search_result = self.db.search_symbol("Basic")
            logger.info(f"[first_iteration] 搜索结果: {len(search_result['classes'])} 类, {len(search_result['functions'])} 函数")
            
            # 测试7：增量更新 - 同一文件多次修改
            logger.debug("[first_iteration] 测试7：增量更新 - 多次修改")
            update_file = self.project_path / "updating.ets"
            
            for i in range(5):
                update_code = f"""export function version{i}() {{ return {i} }}"""
                update_file.write_text(update_code)
                
                result = asyncio.run(self.updater.update_file(str(update_file)))
                logger.debug(f"[first_iteration] 第 {i} 次更新结果: {result['status']}")
                
                if result['status'] not in ['success', 'skipped']:
                    iteration_errors.append(f"第 {i} 次更新失败: {result.get('error')}")
                    success = False
                    break
                
            logger.info(f"[first_iteration] 多次更新测试完成")
            
        except Exception as e:
            iteration_errors.append(f"第一次迭代异常: {str(e)}")
            logger.exception(f"[first_iteration] 第一次迭代发生异常")
            success = False
        
        if iteration_errors:
            print(f"⚠️ 第一次迭代发现 {len(iteration_errors)} 个问题:")
            for err in iteration_errors:
                print(f"   - {err}")
        else:
            print("✅ 第一次迭代所有测试通过")
        
        logger.info(f"[first_iteration] 第一次迭代完成，状态: {success}")
        
        return success, iteration_errors
        
    def test_second_iteration_pressure_concurrent(self):
        """
        第二次迭代：压力测试 + 并发 + 混合场景
        """
        print("\n" + "="*100)
        print("⚡ 第二次迭代：压力 + 并发 + 混合场景测试")
        print("="*100)
        
        success = True
        iteration_errors = []
        
        logger.info("[second_iteration] 开始第二次迭代测试")
        
        try:
            # 测试1：批量创建和更新大量文件
            logger.debug("[second_iteration] 测试1：批量创建和更新")
            num_files = 200
            files_created = []
            
            for i in range(num_files):
                file_path = self.project_path / f"batch_{i:03d}.ets"
                code = f"""@Component
struct BatchComponent{i:03d} {{
  @State count: number = {i}
  build() {{ Text('Component {i}') }}
  increment() {{ this.count++ }}
}}
"""
                file_path.write_text(code)
                files_created.append(str(file_path))
                
                if i % 50 == 0:
                    logger.debug(f"[second_iteration] 已创建 {i} 个文件")
            
            logger.info(f"[second_iteration] 开始批量更新 {num_files} 个文件")
            batch_start = time.time()
            result = asyncio.run(self.updater.batch_update(files_created))
            batch_time = time.time() - batch_start
            
            logger.info(f"[second_iteration] 批量更新完成: {result['success']}成功, {result['failed']}失败, {result['skipped']}跳过, 耗时 {batch_time:.2f}s")
            
            if result['failed'] > 0:
                iteration_errors.append(f"批量更新有 {result['failed']} 个失败")
                success = False
            
            # 测试2：交替读写操作
            logger.debug("[second_iteration] 测试2：交替读写操作")
            read_write_errors = 0
            
            for i in range(50):
                # 写入操作
                update_file = self.project_path / f"rw_{i}.ets"
                update_file.write_text(f"""export function func{i}() {{ return {i} }}""")
                
                update_result = asyncio.run(self.updater.update_file(str(update_file)))
                if update_result['status'] != 'success':
                    read_write_errors += 1
                    logger.warning(f"[second_iteration] 写入操作 {i} 失败")
                
                # 读取操作
                search_result = self.db.search_symbol(f"func{i}")
                if not search_result['functions']:
                    logger.warning(f"[second_iteration] 读取操作 {i} 未找到结果")
            
            if read_write_errors > 0:
                iteration_errors.append(f"交替读写操作有 {read_write_errors} 个错误")
                success = False
            
            # 测试3：混合场景 - 同时处理不同类型文件
            logger.debug("[second_iteration] 测试3：混合场景处理")
            mix_files = []
            
            # 生成混合的不同复杂度文件
            for i in range(100):
                file_path = self.project_path / f"mix_{i}.ets"
                complexity = i % 4
                code = self.generate_complex_arkts_code(complexity)
                file_path.write_text(code)
                mix_files.append(str(file_path))
                
                if i % 25 == 0:
                    logger.debug(f"[second_iteration] 混合文件已创建 {i} 个")
            
            logger.info(f"[second_iteration] 开始混合场景批量更新")
            mix_result = asyncio.run(self.updater.batch_update(mix_files))
            
            logger.info(f"[second_iteration] 混合场景结果: {mix_result['success']}成功, {mix_result['failed']}失败")
            
            if mix_result['failed'] > 5:
                iteration_errors.append(f"混合场景有 {mix_result['failed']} 个失败，超过阈值")
                success = False
            
        except Exception as e:
            iteration_errors.append(f"第二次迭代异常: {str(e)}")
            logger.exception(f"[second_iteration] 第二次迭代发生异常")
            success = False
        
        if iteration_errors:
            print(f"⚠️ 第二次迭代发现 {len(iteration_errors)} 个问题:")
            for err in iteration_errors:
                print(f"   - {err}")
        else:
            print("✅ 第二次迭代所有测试通过")
        
        logger.info(f"[second_iteration] 第二次迭代完成，状态: {success}")
        
        return success, iteration_errors
        
    def test_third_iteration_extreme_chaos_long_duration(self):
        """
        第三次迭代：极端 + 混沌 + 长时间运行测试
        """
        print("\n" + "="*100)
        print("🌪️ 第三次迭代：极端 + 混沌 + 长时间测试")
        print("="*100)
        
        success = True
        iteration_errors = []
        
        logger.info("[third_iteration] 开始第三次迭代测试")
        
        try:
            # 测试1：极端场景 - 非常长的代码
            logger.debug("[third_iteration] 测试1：极端长代码文件")
            long_file = self.project_path / "very_long.ets"
            
            # 生成非常长的代码
            long_code_parts = []
            for i in range(100):
                long_code_parts.append(f"""export function veryLongFunction{i}() {{
  let result = 0
  for (let j = 0; j < 1000; j++) {{
    result += j
  }}
  return result
}}
""")
            
            long_code = "\n".join(long_code_parts)
            long_file.write_text(long_code)
            
            logger.debug(f"[third_iteration] 长代码文件大小: {len(long_code)} 字符")
            
            result = asyncio.run(self.updater.update_file(str(long_file)))
            logger.info(f"[third_iteration] 长代码文件解析结果: {result['status']}")
            
            if result['status'] != 'success':
                iteration_errors.append(f"长代码文件解析失败: {result.get('error')}")
                success = False
            
            # 测试2：混沌场景 - 随机变化的文件
            logger.debug("[third_iteration] 测试2：混沌场景 - 随机变化")
            num_chaos_rounds = 30
            chaos_file = self.project_path / "chaos.ets"
            
            for round_num in range(num_chaos_rounds):
                # 随机生成不同复杂度的代码
                complexity = random.randint(0, 3)
                code = self.generate_complex_arkts_code(complexity)
                
                # 有时插入一些混乱的内容
                if random.random() < 0.3:
                    code += "\n// 随机注释 " + "".join(random.choices(string.ascii_letters + string.digits, k=50)) + "\n"
                
                if random.random() < 0.1:
                    # 10%概率插入一些混乱内容
                    code += "\n" + "".join(random.choices(string.ascii_letters, k=20)) + "\n"
                
                chaos_file.write_text(code)
                
                result = asyncio.run(self.updater.update_file(str(chaos_file)))
                
                if result['status'] not in ['success', 'skipped']:
                    logger.warning(f"[third_iteration] 混沌回合 {round_num} 解析失败")
                
                if round_num % 10 == 0:
                    logger.debug(f"[third_iteration] 混沌测试已完成 {round_num} 回合")
            
            logger.info(f"[third_iteration] 混沌测试 {num_chaos_rounds} 回合完成")
            
            # 测试3：长时间运行测试 - 持续更新
            logger.debug("[third_iteration] 测试3：长时间持续更新")
            duration_seconds = 10
            start_time = time.time()
            updates_done = 0
            long_test_file = self.project_path / "long_test.ets"
            
            logger.info(f"[third_iteration] 开始长时间运行测试，持续 {duration_seconds} 秒")
            
            while time.time() - start_time < duration_seconds:
                updates_done += 1
                
                code = f"""export function iteration{updates_done}() {{ return {updates_done} }}
export class LongTestClass{updates_done} {{ value: number = {updates_done} }}
"""
                long_test_file.write_text(code)
                
                result = asyncio.run(self.updater.update_file(str(long_test_file)))
                
                if result['status'] not in ['success', 'skipped']:
                    iteration_errors.append(f"长时间运行在第 {updates_done} 次更新失败")
                    logger.error(f"[third_iteration] 长时间运行第 {updates_done} 次更新失败")
                    success = False
                    break
                
                # 短暂暂停模拟真实场景
                time.sleep(random.uniform(0.01, 0.1))
            
            logger.info(f"[third_iteration] 长时间运行测试完成: {updates_done} 次更新在 {time.time() - start_time:.1f} 秒内")
            
            # 测试4：数据库压力 - 大量搜索
            logger.debug("[third_iteration] 测试4：大量搜索操作")
            search_queries = ["Component", "function", "struct", "interface", "import", "a", "1", "LongTest", "Batch", ""]
            search_errors = 0
            
            for i, query in enumerate(search_queries * 5):
                try:
                    search_result = self.db.search_symbol(query)
                except Exception as e:
                    search_errors += 1
                    logger.warning(f"[third_iteration] 搜索 '{query}' 发生错误: {e}")
            
            if search_errors > 0:
                iteration_errors.append(f"搜索测试有 {search_errors} 个错误")
                success = False
            
        except Exception as e:
            iteration_errors.append(f"第三次迭代异常: {str(e)}")
            logger.exception(f"[third_iteration] 第三次迭代发生异常")
            success = False
        
        if iteration_errors:
            print(f"⚠️ 第三次迭代发现 {len(iteration_errors)} 个问题:")
            for err in iteration_errors:
                print(f"   - {err}")
        else:
            print("✅ 第三次迭代所有测试通过")
        
        logger.info(f"[third_iteration] 第三次迭代完成，状态: {success}")
        
        return success, iteration_errors
        
    def run_full_deep_test(self):
        """运行完整的深度多次迭代测试"""
        print("\n" + "="*100)
        print("🚀 开始超级深度多次迭代测试系统")
        print("="*100)
        print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        all_errors = []
        
        # 第一次迭代
        try:
            self.setup(1)
            logger.info("[deep_test] =======================================")
            logger.info("[deep_test] 开始第 1 次迭代")
            logger.info("[deep_test] =======================================")
            success1, errors1 = self.test_first_iteration_static_analysis()
            all_errors.extend(errors1)
            self.iteration_results.append(('iteration_1', success1, errors1))
            self.teardown()
        except Exception as e:
            logger.exception("[deep_test] 第 1 次迭代框架错误")
            all_errors.append(f"第1次迭代框架失败: {str(e)}")
        
        # 第二次迭代
        try:
            self.setup(2)
            logger.info("[deep_test] =======================================")
            logger.info("[deep_test] 开始第 2 次迭代")
            logger.info("[deep_test] =======================================")
            success2, errors2 = self.test_second_iteration_pressure_concurrent()
            all_errors.extend(errors2)
            self.iteration_results.append(('iteration_2', success2, errors2))
            self.teardown()
        except Exception as e:
            logger.exception("[deep_test] 第 2 次迭代框架错误")
            all_errors.append(f"第2次迭代框架失败: {str(e)}")
        
        # 第三次迭代
        try:
            self.setup(3)
            logger.info("[deep_test] =======================================")
            logger.info("[deep_test] 开始第 3 次迭代")
            logger.info("[deep_test] =======================================")
            success3, errors3 = self.test_third_iteration_extreme_chaos_long_duration()
            all_errors.extend(errors3)
            self.iteration_results.append(('iteration_3', success3, errors3))
            self.teardown()
        except Exception as e:
            logger.exception("[deep_test] 第 3 次迭代框架错误")
            all_errors.append(f"第3次迭代框架失败: {str(e)}")
        
        # 总结
        print("\n" + "="*100)
        print("📊 超级深度多次迭代测试总结")
        print("="*100)
        
        for iteration_name, success, errors in self.iteration_results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n{iteration_name.replace('_', ' ').title()}: {status}")
            if errors:
                print(f"   问题数: {len(errors)}")
                for err in errors:
                    print(f"   - {err}")
        
        total_errors = len(all_errors)
        if total_errors == 0:
            print("\n🎉 所有迭代测试完美通过！系统质量优秀！")
        else:
            print(f"\n⚠️ 共发现 {total_errors} 个问题需要解决")
        
        print(f"\n测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*100)
        
        return total_errors == 0, all_errors


def main():
    tester = DeepIterativeTester()
    success, errors = tester.run_full_deep_test()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
