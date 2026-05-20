#!/usr/bin/env python3
"""
高强度压力测试系统 - 发现系统缺陷
"""
import os
import sys
import time
import random
import asyncio
import psutil
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import structlog

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.database import CodeGraphDB
from src.incremental import IncrementalUpdater
from src.parser import LocalArkTSParser

logger = structlog.get_logger()

class StressTester:
    def __init__(self, project_path: str, db_path: str = "stress_test.db"):
        self.project_path = Path(project_path)
        self.db_path = db_path
        self.db = None
        self.updater = None
        self.parser = None
        self.results = {
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "warnings": [],
            "performance": [],
            "memory_history": []
        }
    
    def setup(self):
        """初始化测试环境"""
        logger.info("stress_test_setup", project_path=self.project_path)
        
        # 清理旧数据库
        if Path(self.db_path).exists():
            Path(self.db_path).unlink()
        
        self.db = CodeGraphDB(self.db_path)
        self.parser = LocalArkTSParser()
        self.updater = IncrementalUpdater(self.db, self.parser)
        self._record_memory()
    
    def teardown(self):
        """清理测试环境"""
        if self.db:
            self.db.close()
        if Path(self.db_path).exists():
            Path(self.db_path).unlink()
        logger.info("stress_test_teardown")
    
    def _record_memory(self):
        """记录内存使用"""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        self.results["memory_history"].append({
            "timestamp": datetime.now().isoformat(),
            "memory_mb": memory_mb
        })
        return memory_mb
    
    def test_initial_scan(self) -> bool:
        """测试1: 初始全量扫描"""
        print("\n" + "="*80)
        print("测试 1: 初始全量扫描")
        print("="*80)
        
        try:
            start_time = time.time()
            files = list(self.project_path.rglob("*.ets"))
            
            print(f"发现 {len(files)} 个ArkTS文件")
            
            success_count = 0
            for i, file_path in enumerate(files):
                try:
                    result = asyncio.run(self.updater.update_file(str(file_path)))
                    if result["status"] == "success":
                        success_count += 1
                    if (i + 1) % 20 == 0:
                        print(f"  处理进度: {i+1}/{len(files)}")
                        self._record_memory()
                except Exception as e:
                    self.results["errors"].append({
                        "test": "initial_scan",
                        "file": str(file_path),
                        "error": str(e)
                    })
            
            elapsed = time.time() - start_time
            
            # 检查数据库
            cursor = self.db.conn.execute("SELECT COUNT(*) FROM files")
            db_files = cursor.fetchone()[0]
            
            cursor = self.db.conn.execute("SELECT COUNT(*) FROM functions")
            db_functions = cursor.fetchone()[0]
            
            cursor = self.db.conn.execute("SELECT COUNT(*) FROM classes")
            db_classes = cursor.fetchone()[0]
            
            self.results["performance"].append({
                "test": "initial_scan",
                "files": len(files),
                "success": success_count,
                "db_files": db_files,
                "db_functions": db_functions,
                "db_classes": db_classes,
                "time_seconds": elapsed,
                "files_per_second": len(files) / elapsed
            })
            
            print(f"\n✅ 初始扫描完成:")
            print(f"   总文件数: {len(files)}")
            print(f"   成功数: {success_count}")
            print(f"   耗时: {elapsed:.2f}s")
            print(f"   速度: {len(files)/elapsed:.1f} 文件/秒")
            print(f"   数据库: {db_files} 个文件, {db_functions} 个函数, {db_classes} 个类")
            print(f"   当前内存: {self._record_memory():.2f}MB")
            
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            print(f"❌ 初始扫描失败: {e}")
            self.results["errors"].append({
                "test": "initial_scan",
                "error": str(e)
            })
            self.results["tests_failed"] += 1
            return False
    
    def test_incremental_updates(self, num_updates: int = 50) -> bool:
        """测试2: 多次增量更新"""
        print("\n" + "="*80)
        print(f"测试 2: {num_updates} 次增量更新")
        print("="*80)
        
        try:
            files = list(self.project_path.rglob("*.ets"))
            
            start_time = time.time()
            update_times = []
            
            for i in range(num_updates):
                # 随机选择文件进行修改
                target_file = random.choice(files)
                original_content = target_file.read_text(encoding='utf-8')
                
                # 添加一些随机内容
                modified_content = original_content + f"\n\n// Stress test modification #{i+1} - {datetime.now().isoformat()}"
                target_file.write_text(modified_content, encoding='utf-8')
                
                # 执行增量更新
                update_start = time.time()
                try:
                    result = asyncio.run(self.updater.update_file(str(target_file)))
                    update_times.append(time.time() - update_start)
                    
                    if result["status"] != "success":
                        self.results["warnings"].append({
                            "test": "incremental_update",
                            "file": str(target_file),
                            "update": i+1,
                            "result": result
                        })
                except Exception as e:
                    self.results["errors"].append({
                        "test": "incremental_update",
                        "file": str(target_file),
                        "update": i+1,
                        "error": str(e)
                    })
                
                # 恢复原内容
                target_file.write_text(original_content, encoding='utf-8')
                
                if (i + 1) % 10 == 0:
                    print(f"  更新进度: {i+1}/{num_updates}")
                    self._record_memory()
            
            elapsed = time.time() - start_time
            avg_update_time = sum(update_times) / len(update_times) if update_times else 0
            
            self.results["performance"].append({
                "test": "incremental_updates",
                "updates": num_updates,
                "time_seconds": elapsed,
                "avg_update_ms": avg_update_time * 1000
            })
            
            print(f"\n✅ 增量更新测试完成:")
            print(f"   总更新次数: {num_updates}")
            print(f"   耗时: {elapsed:.2f}s")
            print(f"   平均每次: {avg_update_time*1000:.2f}ms")
            print(f"   当前内存: {self._record_memory():.2f}MB")
            
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            print(f"❌ 增量更新测试失败: {e}")
            self.results["errors"].append({
                "test": "incremental_updates",
                "error": str(e)
            })
            self.results["tests_failed"] += 1
            return False
    
    def test_hash_detection(self) -> bool:
        """测试3: 哈希值变化检测"""
        print("\n" + "="*80)
        print("测试 3: 哈希值变化检测")
        print("="*80)
        
        try:
            files = list(self.project_path.rglob("*.ets"))
            test_file = random.choice(files)
            
            original_hash = self.db.compute_file_hash(str(test_file))
            needs_update = self.db.file_needs_update(str(test_file))
            
            original_content = test_file.read_text(encoding='utf-8')
            
            # 情况1: 修改内容后检测
            test_file.write_text(original_content + "\n// Modified", encoding='utf-8')
            modified_hash = self.db.compute_file_hash(str(test_file))
            should_update = self.db.file_needs_update(str(test_file))
            
            # 情况2: 相同内容不更新
            test_file.write_text(original_content, encoding='utf-8')
            restored_hash = self.db.compute_file_hash(str(test_file))
            
            passed = (
                not needs_update and  # 初始不应该更新
                original_hash != modified_hash and  # 内容变化后哈希应该变
                should_update and  # 内容变化后应该检测到更新
                original_hash == restored_hash  # 恢复后哈希应该相同
            )
            
            if passed:
                print(f"\n✅ 哈希检测测试通过:")
                print(f"   原始哈希: {original_hash[:16]}...")
                print(f"   修改后哈希: {modified_hash[:16]}...")
                print(f"   恢复后哈希: {restored_hash[:16]}...")
                self.results["tests_passed"] += 1
            else:
                print(f"❌ 哈希检测测试失败")
                self.results["tests_failed"] += 1
            
            return passed
            
        except Exception as e:
            print(f"❌ 哈希检测测试异常: {e}")
            self.results["errors"].append({
                "test": "hash_detection",
                "error": str(e)
            })
            self.results["tests_failed"] += 1
            return False
    
    def test_concurrent_queries(self, num_queries: int = 100) -> bool:
        """测试4: 并发查询压力"""
        print("\n" + "="*80)
        print(f"测试 4: {num_queries} 次并发查询")
        print("="*80)
        
        try:
            start_time = time.time()
            
            query_types = [
                "SELECT COUNT(*) FROM files",
                "SELECT COUNT(*) FROM functions",
                "SELECT COUNT(*) FROM classes",
                "SELECT * FROM files LIMIT 10",
                "SELECT * FROM functions LIMIT 10",
                "SELECT * FROM classes LIMIT 10",
            ]
            
            success_count = 0
            for i in range(num_queries):
                try:
                    query = random.choice(query_types)
                    cursor = self.db.conn.execute(query)
                    cursor.fetchall()
                    success_count += 1
                except Exception as e:
                    self.results["warnings"].append({
                        "test": "concurrent_queries",
                        "query": i,
                        "error": str(e)
                    })
                
                if (i + 1) % 20 == 0:
                    print(f"  查询进度: {i+1}/{num_queries}")
            
            elapsed = time.time() - start_time
            
            self.results["performance"].append({
                "test": "concurrent_queries",
                "queries": num_queries,
                "success": success_count,
                "time_seconds": elapsed,
                "queries_per_second": num_queries / elapsed
            })
            
            print(f"\n✅ 并发查询测试完成:")
            print(f"   总查询数: {num_queries}")
            print(f"   成功数: {success_count}")
            print(f"   耗时: {elapsed:.2f}s")
            print(f"   速度: {num_queries/elapsed:.0f} 查询/秒")
            
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            print(f"❌ 并发查询测试失败: {e}")
            self.results["errors"].append({
                "test": "concurrent_queries",
                "error": str(e)
            })
            self.results["tests_failed"] += 1
            return False
    
    def test_large_file_handling(self) -> bool:
        """测试5: 大文件处理"""
        print("\n" + "="*80)
        print("测试 5: 大文件处理")
        print("="*80)
        
        try:
            # 创建一个超大文件
            large_file = self.project_path / "large_test_file.ets"
            
            # 生成10000行的大文件
            lines = []
            for i in range(10000):
                lines.append(f"export function testFunction{i}(param{i}: number): number {{ return param{i} * 2; }}")
            
            large_content = "\n".join(lines)
            large_file.write_text(large_content, encoding='utf-8')
            
            file_size_kb = large_file.stat().st_size / 1024
            
            start_time = time.time()
            result = asyncio.run(self.updater.update_file(str(large_file)))
            elapsed = time.time() - start_time
            
            passed = result["status"] == "success"
            
            print(f"\n大文件信息:")
            print(f"   大小: {file_size_kb:.2f}KB")
            print(f"   行数: 10000")
            
            if passed:
                print(f"✅ 大文件处理通过:")
                print(f"   耗时: {elapsed:.2f}s")
                print(f"   解析函数数: {result.get('parsed', {}).get('functions', 0)}")
                self.results["tests_passed"] += 1
            else:
                print(f"❌ 大文件处理失败")
                self.results["tests_failed"] += 1
            
            # 清理
            large_file.unlink()
            return passed
            
        except Exception as e:
            print(f"❌ 大文件处理异常: {e}")
            self.results["errors"].append({
                "test": "large_file",
                "error": str(e)
            })
            self.results["tests_failed"] += 1
            return False
    
    def test_error_recovery(self) -> bool:
        """测试6: 错误恢复能力"""
        print("\n" + "="*80)
        print("测试 6: 错误恢复能力")
        print("="*80)
        
        try:
            files = list(self.project_path.rglob("*.ets"))
            test_file = random.choice(files)
            
            original_content = test_file.read_text(encoding='utf-8')
            
            # 写入损坏的内容
            corrupted_content = original_content + "\nthis is invalid syntax!!! @#$%^&*()"
            test_file.write_text(corrupted_content, encoding='utf-8')
            
            # 尝试解析（应该能优雅处理）
            result = asyncio.run(self.updater.update_file(str(test_file)))
            
            # 恢复原内容并再次解析
            test_file.write_text(original_content, encoding='utf-8')
            recovery_result = asyncio.run(self.updater.update_file(str(test_file)))
            
            passed = recovery_result["status"] == "success"
            
            if passed:
                print(f"✅ 错误恢复测试通过:")
                print(f"   损坏状态处理结果: {result['status']}")
                print(f"   恢复后状态: {recovery_result['status']}")
                self.results["tests_passed"] += 1
            else:
                print(f"❌ 错误恢复测试失败")
                self.results["tests_failed"] += 1
            
            return passed
            
        except Exception as e:
            print(f"❌ 错误恢复测试异常: {e}")
            self.results["errors"].append({
                "test": "error_recovery",
                "error": str(e)
            })
            self.results["tests_failed"] += 1
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        self.setup()
        
        try:
            print("🚀 开始高强度压力测试...")
            print(f"测试项目: {self.project_path}")
            print(f"开始时间: {datetime.now().isoformat()}")
            
            self.test_initial_scan()
            self.test_incremental_updates(50)
            self.test_hash_detection()
            self.test_concurrent_queries(100)
            self.test_large_file_handling()
            self.test_error_recovery()
            
            # 最终内存检测
            final_memory = self._record_memory()
            
            # 输出总结
            print("\n" + "="*80)
            print("📊 压力测试总结")
            print("="*80)
            
            print(f"\n✅ 通过: {self.results['tests_passed']}")
            print(f"❌ 失败: {self.results['tests_failed']}")
            
            if self.results["errors"]:
                print(f"\n⚠️  发现 {len(self.results['errors'])} 个错误:")
                for i, err in enumerate(self.results["errors"][:10]):
                    print(f"   {i+1}. {err.get('test')}: {err.get('error', 'Unknown')}")
            
            if self.results["warnings"]:
                print(f"\n⚠️  发现 {len(self.results['warnings'])} 个警告")
            
            if self.results["performance"]:
                print(f"\n📈 性能数据:")
                for perf in self.results["performance"]:
                    print(f"   - {perf['test']}: {perf}")
            
            if self.results["memory_history"]:
                memory_values = [m["memory_mb"] for m in self.results["memory_history"]]
                print(f"\n💾 内存使用:")
                print(f"   初始: {memory_values[0]:.2f}MB")
                print(f"   峰值: {max(memory_values):.2f}MB")
                print(f"   最终: {final_memory:.2f}MB")
                print(f"   增长: {final_memory - memory_values[0]:.2f}MB")
            
            total_tests = self.results["tests_passed"] + self.results["tests_failed"]
            print(f"\n🎉 测试完成! 成功率: {self.results['tests_passed']/total_tests*100:.0f}%")
            
        finally:
            self.teardown()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="高强度压力测试系统")
    parser.add_argument("--path", default="large-test-project", help="测试项目路径")
    args = parser.parse_args()
    
    # 检查项目是否存在
    if not Path(args.path).exists():
        print(f"❌ 项目路径不存在: {args.path}")
        print("请先运行: python generate_large_project.py")
        return 1
    
    # 运行压力测试
    tester = StressTester(args.path)
    tester.run_all_tests()
    
    return 0

if __name__ == "__main__":
    exit(main())
