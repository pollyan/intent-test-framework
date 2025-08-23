#!/usr/bin/env python3
"""
Intent Test Framework - 性能基准测试工具

用于监控和分析测试套件的性能表现，识别慢速测试并提供优化建议。
"""

import json
import time
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class TestBenchmark:
    """测试基准分析器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results_file = self.project_root / "benchmark_results.json"
        self.threshold_slow = 5.0  # 慢速测试阈值（秒）
        self.threshold_fast = 1.0  # 快速测试阈值（秒）

    def run_benchmark(
        self, test_path: str = "tests/api", parallel: bool = False
    ) -> Dict[str, Any]:
        """运行性能基准测试"""
        print(f"🚀 开始性能基准测试: {test_path}")
        start_time = time.time()

        # 构建pytest命令
        cmd = [
            "python",
            "-m",
            "pytest",
            test_path,
            "--durations=0",  # 显示所有测试的执行时间
            "--tb=no",  # 不显示traceback以减少输出
            "-v",
            (
                "--benchmark-json=benchmark.json"
                if self._has_benchmark_plugin()
                else "--json-report"
            ),
        ]

        if parallel and self._has_xdist():
            cmd.extend(["-n", "auto", "--dist", "worksteal"])

        # 运行测试
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )

            execution_time = time.time() - start_time

            # 解析结果
            benchmark_data = self._parse_pytest_output(result.stdout, result.stderr)
            benchmark_data.update(
                {
                    "total_execution_time": execution_time,
                    "parallel_enabled": parallel,
                    "test_path": test_path,
                    "timestamp": datetime.now().isoformat(),
                    "exit_code": result.returncode,
                }
            )

            return benchmark_data

        except subprocess.TimeoutExpired:
            print("❌ 测试执行超时（5分钟）")
            return {"error": "timeout", "execution_time": 300}
        except Exception as e:
            print(f"❌ 测试执行失败: {e}")
            return {"error": str(e)}

    def _parse_pytest_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """解析pytest输出，提取性能数据"""
        data = {
            "tests": [],
            "slow_tests": [],
            "fast_tests": [],
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "warnings": [],
        }

        # 解析测试结果统计
        for line in stdout.split("\n"):
            if "passed" in line and ("failed" in line or "error" in line):
                # 解析测试统计行，如：25 passed, 2 failed in 10.20s
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed":
                        data["passed"] = int(parts[i - 1])
                    elif part == "failed":
                        data["failed"] = int(parts[i - 1])
                    elif part == "error":
                        data["errors"] = int(parts[i - 1])

            # 解析慢速测试
            if "SLOWEST TEST DURATIONS" in line or "slowest durations" in line:
                slow_tests = self._extract_slow_tests(stdout[stdout.find(line) :])
                data["slow_tests"].extend(slow_tests)

        data["total_tests"] = data["passed"] + data["failed"] + data["errors"]

        # 分类测试
        for test in data["slow_tests"]:
            if test["duration"] > self.threshold_slow:
                test["category"] = "slow"
            elif test["duration"] < self.threshold_fast:
                test["category"] = "fast"
            else:
                test["category"] = "medium"

        return data

    def _extract_slow_tests(self, durations_section: str) -> List[Dict[str, Any]]:
        """从pytest输出中提取慢速测试信息"""
        tests = []
        lines = durations_section.split("\n")

        for line in lines:
            # 匹配格式: 1.23s call tests/api/test_example.py::test_function
            if "s call " in line and "::" in line:
                try:
                    parts = line.split("s call ")
                    if len(parts) == 2:
                        duration = float(parts[0].strip())
                        test_path = parts[1].strip()

                        tests.append(
                            {"test": test_path, "duration": duration, "phase": "call"}
                        )
                except ValueError:
                    continue

        return tests

    def analyze_performance(self, benchmark_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析性能数据并生成报告"""
        analysis = {
            "summary": {},
            "recommendations": [],
            "slow_test_analysis": {},
            "performance_score": 0,
        }

        # 基本统计
        total_time = benchmark_data.get("total_execution_time", 0)
        total_tests = benchmark_data.get("total_tests", 0)
        slow_tests = benchmark_data.get("slow_tests", [])

        analysis["summary"] = {
            "total_execution_time": total_time,
            "total_tests": total_tests,
            "average_test_time": total_time / max(total_tests, 1),
            "slow_test_count": len(
                [t for t in slow_tests if t["duration"] > self.threshold_slow]
            ),
            "fast_test_count": len(
                [t for t in slow_tests if t["duration"] < self.threshold_fast]
            ),
        }

        # 性能评分（0-100）
        avg_time = analysis["summary"]["average_test_time"]
        slow_ratio = analysis["summary"]["slow_test_count"] / max(total_tests, 1)

        # 基础分数：基于平均测试时间
        if avg_time < 0.5:
            time_score = 100
        elif avg_time < 1.0:
            time_score = 80
        elif avg_time < 2.0:
            time_score = 60
        else:
            time_score = max(0, 60 - (avg_time - 2) * 10)

        # 慢速测试惩罚
        slow_penalty = slow_ratio * 30

        analysis["performance_score"] = max(0, int(time_score - slow_penalty))

        # 生成建议
        analysis["recommendations"] = self._generate_recommendations(
            analysis["summary"]
        )

        return analysis

    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """生成性能优化建议"""
        recommendations = []

        avg_time = summary["average_test_time"]
        slow_count = summary["slow_test_count"]
        fast_count = summary["fast_test_count"]
        total_tests = summary["total_tests"]

        # 平均时间建议
        if avg_time > 2.0:
            recommendations.append("⚠️ 平均测试时间过长，建议优化测试数据准备和清理逻辑")
        elif avg_time > 1.0:
            recommendations.append("💡 考虑使用测试数据工厂和内存数据库加速测试")

        # 慢速测试建议
        if slow_count > total_tests * 0.1:  # 超过10%的测试是慢速的
            recommendations.append(
                "🐌 发现过多慢速测试，建议使用@pytest.mark.slow标记并在快速测试中排除"
            )
            recommendations.append("📊 考虑将慢速测试拆分为更小的测试单元")

        # 并行化建议
        if total_tests > 10 and not recommendations:
            recommendations.append(
                "🚀 测试数量较多，建议启用并行测试: pip install pytest-xdist"
            )

        # 快速测试比例建议
        fast_ratio = fast_count / max(total_tests, 1)
        if fast_ratio < 0.5:
            recommendations.append("⚡ 快速测试比例较低，建议优化测试设计和数据准备")

        if not recommendations:
            recommendations.append("✅ 测试性能表现良好，继续保持！")

        return recommendations

    def save_results(self, benchmark_data: Dict[str, Any], analysis: Dict[str, Any]):
        """保存基准测试结果"""
        results = {
            "benchmark": benchmark_data,
            "analysis": analysis,
            "generated_at": datetime.now().isoformat(),
        }

        # 读取历史数据
        history = []
        if self.results_file.exists():
            try:
                with open(self.results_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        history = data
                    else:
                        history = [data]  # 兼容旧格式
            except:
                pass

        # 添加新结果（保留最近10次）
        history.append(results)
        history = history[-10:]

        # 保存
        with open(self.results_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def print_report(self, analysis: Dict[str, Any]):
        """打印性能分析报告"""
        print("\n" + "=" * 60)
        print("📊 性能基准测试报告")
        print("=" * 60)

        summary = analysis["summary"]
        print(f"📈 性能评分: {analysis['performance_score']}/100")
        print(f"⏱️  总执行时间: {summary['total_execution_time']:.2f}秒")
        print(f"🧪 测试总数: {summary['total_tests']}")
        print(f"📊 平均测试时间: {summary['average_test_time']:.3f}秒")
        print(f"🐌 慢速测试: {summary['slow_test_count']} (>{self.threshold_slow}s)")
        print(f"⚡ 快速测试: {summary['fast_test_count']} (<{self.threshold_fast}s)")

        print(f"\n💡 优化建议:")
        for i, rec in enumerate(analysis["recommendations"], 1):
            print(f"  {i}. {rec}")

        print("\n" + "=" * 60)

    def _has_benchmark_plugin(self) -> bool:
        """检查是否安装了pytest-benchmark插件"""
        try:
            import pytest_benchmark

            return True
        except ImportError:
            return False

    def _has_xdist(self) -> bool:
        """检查是否安装了pytest-xdist插件"""
        try:
            import xdist

            return True
        except ImportError:
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Intent Test Framework 性能基准测试工具"
    )
    parser.add_argument(
        "--path", default="tests/api", help="测试路径 (默认: tests/api)"
    )
    parser.add_argument("--parallel", action="store_true", help="启用并行测试")
    parser.add_argument("--save", action="store_true", help="保存结果到文件")
    parser.add_argument("--report-only", action="store_true", help="只显示最新报告")

    args = parser.parse_args()

    benchmark = TestBenchmark()

    if args.report_only:
        # 只显示最新报告
        if benchmark.results_file.exists():
            with open(benchmark.results_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    latest = data[-1]
                    benchmark.print_report(latest["analysis"])
                else:
                    print("❌ 没有找到历史基准测试数据")
        else:
            print("❌ 没有找到基准测试结果文件")
        return

    # 运行基准测试
    benchmark_data = benchmark.run_benchmark(args.path, args.parallel)

    if "error" in benchmark_data:
        print(f"❌ 基准测试失败: {benchmark_data['error']}")
        sys.exit(1)

    # 分析性能
    analysis = benchmark.analyze_performance(benchmark_data)

    # 显示报告
    benchmark.print_report(analysis)

    # 保存结果
    if args.save:
        benchmark.save_results(benchmark_data, analysis)
        print(f"💾 结果已保存到: {benchmark.results_file}")


if __name__ == "__main__":
    main()
