#!/usr/bin/env python3
"""
真实运行时压力测试套件 - 专门发现真实运行时的bug
"""
import os
import sys
import time
import random
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import structlog

sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

logger = structlog.get_logger()


class RuntimeTester:
    """真实运行时测试器"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.db_path = Path(tempfile.mktemp(suffix='.db'))
        self.db = None
        self.parser = None
        self.updater = None
        self.errors = []
        self.warnings = []
        self.metrics = {}
        self.start_time = None
        
    def setup(self):
        """设置测试环境"""
        logger.info("runtime_test_setup", db_path=self.db_path)
        self.db = CodeGraphDB(str(self.db_path))
        self.parser = LocalArkTSParser()
        self.updater = IncrementalUpdater(self.db, self.parser)
        self.start_time = time.time()
        
    def teardown(self):
        """清理测试环境"""
        if self.db:
            self.db.close()
        if self.db_path.exists():
            self.db_path.unlink()
        logger.info("runtime_test_teardown")
        
    def test_empty_files(self):
        """测试空文件处理"""
        print("\n" + "="*80)
        print("Test 1: 空文件处理")
        print("="*80)
        
        success = True
        temp_files = []
        
        try:
            # 创建空文件
            empty_file = self.project_path / "empty_test.ets"
            empty_file.write_text("")
            temp_files.append(empty_file)
            
            result = asyncio.run(self.updater.update_file(str(empty_file)))
            print(f"空文件解析结果: {result['status']}")
            
            # 检查是否崩溃
            assert result['status'] in ['success', 'skipped'], "空文件应该成功处理或跳过"
            
            # 只有空白字符的文件
            whitespace_file = self.project_path / "whitespace_test.ets"
            whitespace_file.write_text("\n   \t\n  \n")
            temp_files.append(whitespace_file)
            
            result = asyncio.run(self.updater.update_file(str(whitespace_file)))
            print(f"空白字符文件解析结果: {result['status']}")
            
            print("✓ 空文件处理测试通过")
            
        except Exception as e:
            print(f"✗ 空文件处理测试失败: {e}")
            self.errors.append({
                "test": "empty_files",
                "error": str(e)
            })
            success = False
        finally:
            for f in temp_files:
                if f.exists():
                    f.unlink()
        
        return success
        
    def test_malformed_code(self):
        """测试格式错误的代码"""
        print("\n" + "="*80)
        print("Test 2: 格式错误的代码处理")
        print("="*80)
        
        success = True
        temp_files = []
        
        try:
            malformed_cases = [
                ("unclosed_brace", """
export function test() {
    console.log("test"
// 缺少闭合括号
"""),
                ("invalid_syntax", """
@#$%^&*() invalid characters
export class Test {
    broken code here
}
"""),
                ("incomplete_statement", """
export const x = 
"""),
            ]
            
            for name, code in malformed_cases:
                file_path = self.project_path / f"malformed_{name}.ets"
                file_path.write_text(code)
                temp_files.append(file_path)
                
                result = asyncio.run(self.updater.update_file(str(file_path)))
                print(f"{name}: {result['status']}")
                
                # 即使代码有问题，系统也不应该崩溃
                assert result['status'] in ['success', 'error'], "系统不应该崩溃"
                
            print("✓ 格式错误代码处理测试通过")
            
        except Exception as e:
            print(f"✗ 格式错误代码处理测试失败: {e}")
            self.errors.append({
                "test": "malformed_code",
                "error": str(e)
            })
            success = False
        finally:
            for f in temp_files:
                if f.exists():
                    f.unlink()
        
        return success
        
    def test_concurrent_operations(self):
        """测试并发操作"""
        print("\n" + "="*80)
        print("Test 3: 并发操作测试")
        print("="*80)
        
        success = True
        threads = []
        results = []
        
        try:
            files = list(self.project_path.glob("**/*.ets"))[:10]
            
            def update_file_thread(file_path):
                try:
                    result = asyncio.run(self.updater.update_file(str(file_path)))
                    results.append((file_path, result))
                except Exception as e:
                    results.append((file_path, {"status": "error", "error": str(e)}))
            
            # 启动多个线程
            for _ in range(5):
                for file_path in files:
                    t = threading.Thread(target=update_file_thread, args=(file_path,))
                    threads.append(t)
                    t.start()
                    time.sleep(0.01)
            
            # 等待所有线程完成
            for t in threads:
                t.join()
            
            error_count = sum(1 for _, r in results if r.get('status') == 'error')
            print(f"并发操作完成: {len(results)} 次, 错误: {error_count}")
            
            if error_count == 0:
                print("✓ 并发操作测试通过")
            else:
                print(f"⚠ 发现 {error_count} 个错误")
                success = False
            
        except Exception as e:
            print(f"✗ 并发操作测试失败: {e}")
            self.errors.append({
                "test": "concurrent_operations",
                "error": str(e)
            })
            success = False
        
        return success
        
    def test_rapid_changes(self):
        """测试快速变化的文件"""
        print("\n" + "="*80)
        print("Test 4: 快速文件变化测试")
        print("="*80)
        
        success = True
        temp_file = self.project_path / "rapid_changes_test.ets"
        
        try:
            base_code = """
export function test() {
    return %s;
}
"""
            
            # 快速修改文件 50 次
            for i in range(50):
                code = base_code % i
                temp_file.write_text(code)
                time.sleep(0.01)
                
                # 尝试更新
                result = asyncio.run(self.updater.update_file(str(temp_file)))
                
                if i % 10 == 0:
                    print(f"变化 {i}: {result['status']}")
            
            print("✓ 快速文件变化测试通过")
            
        except Exception as e:
            print(f"✗ 快速文件变化测试失败: {e}")
            self.errors.append({
                "test": "rapid_changes",
                "error": str(e)
            })
            success = False
        finally:
            if temp_file.exists():
                temp_file.unlink()
        
        return success
        
    def test_database_integrity(self):
        """测试数据库完整性"""
        print("\n" + "="*80)
        print("Test 5: 数据库完整性测试")
        print("="*80)
        
        success = True
        
        try:
            # 先扫描一些文件
            files = list(self.project_path.glob("**/*.ets"))[:15]
            for file_path in files:
                asyncio.run(self.updater.update_file(str(file_path)))
            
            # 检查数据库一致性
            cursor = self.db.conn.execute("SELECT COUNT(*) FROM files")
            file_count = cursor.fetchone()[0]
            
            cursor = self.db.conn.execute("SELECT COUNT(*) FROM functions")
            func_count = cursor.fetchone()[0]
            
            cursor = self.db.conn.execute("SELECT COUNT(*) FROM classes")
            class_count = cursor.fetchone()[0]
            
            print(f"数据库统计: {file_count} 个文件, {func_count} 个函数, {class_count} 个类")
            
            # 检查外键约束
            try:
                cursor = self.db.conn.execute("""
                    SELECT COUNT(*) FROM functions 
                    WHERE file_id NOT IN (SELECT id FROM files)
                """)
                orphan_funcs = cursor.fetchone()[0]
                if orphan_funcs > 0:
                    print(f"⚠ 发现 {orphan_funcs} 个孤立函数记录")
                    success = False
            except Exception as e:
                print(f"外键检查失败: {e}")
                success = False
            
            if success:
                print("✓ 数据库完整性测试通过")
            
        except Exception as e:
            print(f"✗ 数据库完整性测试失败: {e}")
            self.errors.append({
                "test": "database_integrity",
                "error": str(e)
            })
            success = False
        
        return success
        
    def test_extreme_file_sizes(self):
        """测试极端文件大小"""
        print("\n" + "="*80)
        print("Test 6: 极端文件大小测试")
        print("="*80)
        
        success = True
        temp_files = []
        
        try:
            # 极小文件
            tiny_file = self.project_path / "tiny.ets"
            tiny_file.write_text("export const x = 1;")
            temp_files.append(tiny_file)
            
            result = asyncio.run(self.updater.update_file(str(tiny_file)))
            print(f"极小文件 (22字节): {result['status']}")
            
            # 大文件 - 1000个函数
            large_file = self.project_path / "large.ets"
            functions = []
            for i in range(1000):
                functions.append(f"""export function func{i}(param{i}: number): number {{
    return param{i} + {i};
}}""")
            large_code = "\n\n".join(functions)
            large_file.write_text(large_code)
            temp_files.append(large_file)
            
            start = time.time()
            result = asyncio.run(self.updater.update_file(str(large_file)))
            elapsed = time.time() - start
            
            print(f"大文件 (~{len(large_code)} 字节): {result['status']}, 耗时 {elapsed:.2f}秒")
            
            if result['status'] == 'success':
                print("✓ 极端文件大小测试通过")
            else:
                success = False
            
        except Exception as e:
            print(f"✗ 极端文件大小测试失败: {e}")
            self.errors.append({
                "test": "extreme_file_sizes",
                "error": str(e)
            })
            success = False
        finally:
            for f in temp_files:
                if f.exists():
                    f.unlink()
        
        return success
        
    def test_special_characters(self):
        """测试特殊字符"""
        print("\n" + "="*80)
        print("Test 7: 特殊字符处理")
        print("="*80)
        
        success = True
        temp_files = []
        
        try:
            special_cases = [
                ("unicode", """
// 包含 unicode 字符: 你好世界 🌍
export const greeting = "Hello 世界! 🌍";
"""),
                ("escape_chars", """
export const s = "Line1\\nLine2\\tTabbed";
"""),
                ("comments_only", """
/* 多行注释
   包含特殊字符: @#$%^&*
*/
// 单行注释
"""),
            ]
            
            for name, code in special_cases:
                file_path = self.project_path / f"special_{name}.ets"
                file_path.write_text(code)
                temp_files.append(file_path)
                
                result = asyncio.run(self.updater.update_file(str(file_path)))
                print(f"{name}: {result['status']}")
            
            print("✓ 特殊字符处理测试通过")
            
        except Exception as e:
            print(f"✗ 特殊字符处理测试失败: {e}")
            self.errors.append({
                "test": "special_characters",
                "error": str(e)
            })
            success = False
        finally:
            for f in temp_files:
                if f.exists():
                    f.unlink()
        
        return success
        
    def run_all_tests(self):
        """运行所有真实运行时测试"""
        self.setup()
        
        print("🚀 开始真实运行时压力测试...")
        print(f"测试项目: {self.project_path}")
        print(f"开始时间: {datetime.now().isoformat()}")
        
        results = {}
        
        try:
            results['empty_files'] = self.test_empty_files()
            results['malformed_code'] = self.test_malformed_code()
            results['concurrent_operations'] = self.test_concurrent_operations()
            results['rapid_changes'] = self.test_rapid_changes()
            results['database_integrity'] = self.test_database_integrity()
            results['extreme_file_sizes'] = self.test_extreme_file_sizes()
            results['special_characters'] = self.test_special_characters()
            
            print("\n" + "="*80)
            print("📊 真实运行时测试总结")
            print("="*80)
            
            passed = sum(1 for v in results.values() if v)
            total = len(results)
            
            for test_name, passed_flag in results.items():
                status = "✓ PASSED" if passed_flag else "✗ FAILED"
                print(f"  {test_name}: {status}")
            
            print(f"\n总测试: {total}, 通过: {passed}, 失败: {total-passed}")
            
            if self.errors:
                print(f"\n⚠ 发现 {len(self.errors)} 个错误:")
                for i, err in enumerate(self.errors[:10]):
                    print(f"  {i+1}. [{err['test']}] {err['error']}")
                if len(self.errors) > 10:
                    print(f"  ... 还有 {len(self.errors) - 10} 个错误")
            
            elapsed = time.time() - self.start_time
            print(f"\n总耗时: {elapsed:.2f} 秒")
            
            return passed == total
            
        finally:
            self.teardown()


if __name__ == "__main__":
    import asyncio
    
    tester = RuntimeTester("large-test-project")
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
