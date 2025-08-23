"""
测试性能优化配置
提供测试执行的性能调优和监控功能
"""

import time
import functools
import threading
from typing import Dict, List, Any
from contextlib import contextmanager


class TestPerformanceMonitor:
    """测试性能监控器"""
    
    def __init__(self):
        self.test_times: Dict[str, float] = {}
        self.slow_tests: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        self.slow_test_threshold = 2.0  # 2秒
        self.very_slow_threshold = 5.0  # 5秒
    
    def record_test_time(self, test_name: str, duration: float):
        """记录测试执行时间"""
        with self.lock:
            self.test_times[test_name] = duration
            
            if duration > self.slow_test_threshold:
                self.slow_tests.append({
                    'name': test_name,
                    'duration': duration,
                    'severity': 'very_slow' if duration > self.very_slow_threshold else 'slow'
                })
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        with self.lock:
            if not self.test_times:
                return {'total_tests': 0, 'avg_time': 0, 'slow_tests': []}
            
            total_time = sum(self.test_times.values())
            avg_time = total_time / len(self.test_times)
            
            return {
                'total_tests': len(self.test_times),
                'total_time': total_time,
                'avg_time': avg_time,
                'slow_tests': sorted(self.slow_tests, key=lambda x: x['duration'], reverse=True),
                'fastest_test': min(self.test_times.items(), key=lambda x: x[1]),
                'slowest_test': max(self.test_times.items(), key=lambda x: x[1])
            }
    
    @contextmanager
    def monitor_test(self, test_name: str):
        """测试监控上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_test_time(test_name, duration)


# 全局性能监控实例
performance_monitor = TestPerformanceMonitor()


def performance_test(threshold: float = 2.0):
    """性能测试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            test_name = f"{func.__module__}.{func.__qualname__}"
            
            with performance_monitor.monitor_test(test_name):
                result = func(*args, **kwargs)
            
            # 检查是否超过阈值
            duration = performance_monitor.test_times.get(test_name, 0)
            if duration > threshold:
                print(f"⚠️ 慢速测试警告: {test_name} 耗时 {duration:.2f}s (阈值: {threshold}s)")
            
            return result
        return wrapper
    return decorator


class DatabaseOptimizer:
    """数据库测试优化器"""
    
    @staticmethod
    def configure_sqlite_for_testing():
        """为测试优化SQLite配置"""
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if 'sqlite' in str(dbapi_connection):
                cursor = dbapi_connection.cursor()
                # 性能优化配置
                cursor.execute("PRAGMA synchronous = OFF")  # 异步写入
                cursor.execute("PRAGMA journal_mode = MEMORY")  # 内存日志
                cursor.execute("PRAGMA temp_store = MEMORY")  # 内存临时存储
                cursor.execute("PRAGMA cache_size = -64000")  # 64MB缓存
                cursor.execute("PRAGMA foreign_keys = ON")  # 启用外键
                cursor.close()
    
    @staticmethod
    def batch_insert_testdata(session, model_class, data_list):
        """批量插入测试数据"""
        if not data_list:
            return []
        
        # 使用bulk_insert_mappings提高性能
        session.bulk_insert_mappings(model_class, data_list)
        session.commit()
        return data_list


class APITestOptimizer:
    """API测试优化器"""
    
    def __init__(self):
        self.request_cache = {}
        self.session_pool = []
    
    def cache_response(self, key: str, response_data: Any):
        """缓存API响应"""
        self.request_cache[key] = response_data
    
    def get_cached_response(self, key: str):
        """获取缓存的API响应"""
        return self.request_cache.get(key)
    
    @staticmethod
    def optimize_flask_test_client(app):
        """优化Flask测试客户端"""
        # 禁用不必要的中间件
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['LOGIN_DISABLED'] = True
        
        # 优化数据库连接
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_size': 5,
            'max_overflow': 10
        }
        
        return app


class ParallelTestManager:
    """并行测试管理器"""
    
    @staticmethod
    def get_optimal_worker_count():
        """获取最优的工作进程数"""
        import os
        import multiprocessing
        
        cpu_count = multiprocessing.cpu_count()
        
        # 考虑内存限制
        available_memory_gb = 8  # 假设8GB可用内存
        memory_per_worker = 0.5  # 每个worker大约需要512MB
        
        max_workers_by_memory = int(available_memory_gb / memory_per_worker)
        
        # 取CPU数量和内存限制的最小值
        optimal_workers = min(cpu_count, max_workers_by_memory, 8)  # 最多8个worker
        
        return max(1, optimal_workers)
    
    @staticmethod
    def group_tests_by_speed(test_files):
        """按测试速度分组测试文件"""
        fast_tests = []
        slow_tests = []
        
        # 这里可以基于历史数据或文件大小来分类
        for test_file in test_files:
            if 'error_scenarios' in test_file or 'integration' in test_file:
                slow_tests.append(test_file)
            else:
                fast_tests.append(test_file)
        
        return fast_tests, slow_tests


class TestResourceManager:
    """测试资源管理器"""
    
    def __init__(self):
        self.resource_pool = {}
        self.cleanup_callbacks = []
    
    def register_resource(self, name: str, resource: Any):
        """注册测试资源"""
        self.resource_pool[name] = resource
    
    def get_resource(self, name: str):
        """获取测试资源"""
        return self.resource_pool.get(name)
    
    def register_cleanup(self, callback):
        """注册清理回调"""
        self.cleanup_callbacks.append(callback)
    
    def cleanup_all(self):
        """清理所有资源"""
        for callback in reversed(self.cleanup_callbacks):
            try:
                callback()
            except Exception as e:
                print(f"清理资源时出错: {e}")
        
        self.resource_pool.clear()
        self.cleanup_callbacks.clear()


# 全局资源管理器
resource_manager = TestResourceManager()


def setup_test_performance_monitoring():
    """设置测试性能监控"""
    import pytest
    import atexit
    
    def print_performance_report():
        """打印性能报告"""
        report = performance_monitor.get_performance_report()
        if report['total_tests'] > 0:
            print("\n" + "="*60)
            print("📊 测试性能报告")
            print("="*60)
            print(f"总测试数量: {report['total_tests']}")
            print(f"总执行时间: {report['total_time']:.2f}s")
            print(f"平均执行时间: {report['avg_time']:.2f}s")
            
            if report['slow_tests']:
                print(f"\n⚠️ 慢速测试 ({len(report['slow_tests'])} 个):")
                for test in report['slow_tests'][:5]:  # 显示前5个最慢的
                    severity_icon = "🐌" if test['severity'] == 'very_slow' else "⏰"
                    print(f"  {severity_icon} {test['name']}: {test['duration']:.2f}s")
            
            fastest_name, fastest_time = report['fastest_test']
            slowest_name, slowest_time = report['slowest_test']
            print(f"\n⚡ 最快测试: {fastest_name} ({fastest_time:.2f}s)")
            print(f"🐌 最慢测试: {slowest_name} ({slowest_time:.2f}s)")
    
    # 注册退出时打印报告
    atexit.register(print_performance_report)


def pytest_configure():
    """Pytest配置钩子"""
    setup_test_performance_monitoring()
    DatabaseOptimizer.configure_sqlite_for_testing()


def pytest_collection_modifyitems(config, items):
    """修改测试收集，优化执行顺序"""
    # 按测试类型排序：快速测试优先
    def sort_key(item):
        # 检查标记
        if item.get_closest_marker('fast'):
            return 0
        elif item.get_closest_marker('slow'):
            return 2
        else:
            return 1
    
    items.sort(key=sort_key)


# 测试配置类
class TestConfig:
    """测试配置"""
    
    # 性能阈值
    SLOW_TEST_THRESHOLD = 2.0  # 2秒
    VERY_SLOW_TEST_THRESHOLD = 5.0  # 5秒
    
    # 数据库配置
    TEST_DATABASE_URI = 'sqlite:///:memory:'
    DATABASE_POOL_SIZE = 5
    DATABASE_MAX_OVERFLOW = 10
    
    # API测试配置
    API_TIMEOUT = 5.0  # 5秒超时
    MAX_CONCURRENT_REQUESTS = 10
    
    # 资源限制
    MAX_MEMORY_MB = 512  # 每个测试进程最大内存
    MAX_TEST_DURATION = 30  # 30秒最大测试时长
    
    # Mock配置
    ENABLE_EXTERNAL_API_MOCKS = True
    MOCK_RESPONSE_DELAY = 0.1  # 100ms模拟网络延迟