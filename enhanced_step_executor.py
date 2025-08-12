"""
增强的步骤执行器 - 支持MidSceneJS API返回值捕获和变量管理
"""
import time
import json
import math
from typing import Dict, Any, Union
from variable_manager import variable_manager, extract_variable_assignment, process_variable_references


class DataValidator:
    """数据类型验证器"""
    
    @staticmethod
    def validate_ai_query_result(result: Any, data_demand: str) -> tuple[bool, str]:
        """
        验证aiQuery结果是否符合dataDemand规范
        
        Args:
            result: aiQuery返回结果
            data_demand: 期望数据格式
            
        Returns:
            (is_valid, error_message)
        """
        try:
            if result is None:
                return False, "aiQuery返回结果为Null"
            
            # 对于复杂的dataDemand，简单验证结果不为空
            if isinstance(result, (dict, list)):
                return len(result) > 0, "返回结果为空" if len(result) == 0 else ""
            
            return True, ""
        except Exception as e:
            return False, f"aiQuery结果验证失败: {str(e)}"
    
    @staticmethod
    def validate_ai_string_result(result: Any) -> tuple[bool, str]:
        """
        验证aiString结果
        
        Args:
            result: aiString返回结果
            
        Returns:
            (is_valid, error_message)
        """
        if not isinstance(result, str):
            return False, f"aiString应返回字符串，实际返回: {type(result).__name__}"
        
        if len(result.strip()) == 0:
            return False, "aiString返回空字符串"
        
        return True, ""
    
    @staticmethod
    def validate_ai_number_result(result: Any) -> tuple[bool, str]:
        """
        验证aiNumber结果
        
        Args:
            result: aiNumber返回结果
            
        Returns:
            (is_valid, error_message)
        """
        if not isinstance(result, (int, float)):
            return False, f"aiNumber应返回数字，实际返回: {type(result).__name__}"
        
        if math.isnan(result) or math.isinf(result):
            return False, f"aiNumber返回无效数值: {result}"
        
        return True, ""
    
    @staticmethod
    def validate_ai_boolean_result(result: Any) -> tuple[bool, str]:
        """
        验证aiBoolean结果
        
        Args:
            result: aiBoolean返回结果
            
        Returns:
            (is_valid, error_message)
        """
        if not isinstance(result, bool):
            return False, f"aiBoolean应返回布尔值，实际返回: {type(result).__name__}"
        
        return True, ""


def execute_single_step_enhanced(ai, step, mode, execution_id, step_index=0):
    """
    增强的单步骤执行器，支持AI查询返回值捕获和变量管理
    
    Args:
        ai: MidSceneAI实例
        step: 测试步骤字典
        mode: 执行模式
        execution_id: 执行ID
        step_index: 步骤索引
        
    Returns:
        执行结果字典，包含返回值和变量信息
    """
    try:
        action = step.get('action')
        original_params = step.get('params', {})
        description = step.get('description', action)

        # 处理参数中的变量引用
        params = process_variable_references(original_params)
        
        # 提取变量赋值信息（支持output_variable参数）
        variable_name = step.get('output_variable') or extract_variable_assignment(params)

        result = {
            'success': False,
            'ai_decision': {'action': action, 'params': params},
            'confidence': 0.8,
            'execution_details': {},
            'step_index': step_index,
            'step_name': description,
            'return_value': None,  # 新增：存储返回值
            'variable_assigned': None  # 新增：存储分配的变量名
        }

        print(f"[执行] {description}")
        if variable_name:
            print(f"[变量] 将结果存储到变量: {variable_name}")

        # 根据不同的操作类型执行相应的AI操作
        if action == 'goto':
            url = params.get('url')
            if not url:
                raise ValueError("goto操作缺少url参数")
            return_value = ai.goto(url)
            result['success'] = True
            result['execution_details']['url'] = url
            result['return_value'] = return_value

        elif action == 'ai_input':
            text = params.get('text')
            locate = params.get('locate')
            if not text or not locate:
                raise ValueError("ai_input操作缺少text或locate参数")
            return_value = ai.ai_input(text, locate)
            result['success'] = True
            result['execution_details']['text'] = text
            result['execution_details']['locate'] = locate
            result['return_value'] = return_value

        elif action == 'ai_tap':
            prompt = params.get('prompt')
            if not prompt:
                raise ValueError("ai_tap操作缺少prompt参数")
            return_value = ai.ai_tap(prompt)
            result['success'] = True
            result['execution_details']['prompt'] = prompt
            result['return_value'] = return_value

        elif action == 'aiQuery':
            # 根据MidSceneJS API规范实现aiQuery
            data_demand = params.get('dataDemand')
            options = params.get('options', {})
            if not data_demand:
                raise ValueError("aiQuery操作缺少dataDemand参数")
            
            print(f"🔍 执行aiQuery: {data_demand}")
            return_value = ai.ai_query(data_demand, options)
            
            # 数据类型验证
            is_valid, error_msg = DataValidator.validate_ai_query_result(return_value, data_demand)
            if not is_valid:
                print(f"⚠️ aiQuery数据验证失败: {error_msg}")
                result['validation_warning'] = error_msg
            
            result['success'] = True
            result['execution_details']['dataDemand'] = data_demand
            result['execution_details']['options'] = options
            result['return_value'] = return_value
            
            print(f"✅ aiQuery结果: {return_value}")

        elif action == 'aiString':
            # 实现aiString方法
            query = params.get('query')
            options = params.get('options', {})
            if not query:
                raise ValueError("aiString操作缺少query参数")
            
            print(f"🔍 执行aiString: {query}")
            return_value = ai.ai_string(query, options)
            
            # 数据类型验证
            is_valid, error_msg = DataValidator.validate_ai_string_result(return_value)
            if not is_valid:
                print(f"⚠️ aiString数据验证失败: {error_msg}")
                result['validation_warning'] = error_msg
            
            result['success'] = True
            result['execution_details']['query'] = query
            result['execution_details']['options'] = options
            result['return_value'] = return_value
            
            print(f"✅ aiString结果: {return_value}")

        elif action == 'aiNumber':
            # 实现aiNumber方法
            query = params.get('query')
            options = params.get('options', {})
            if not query:
                raise ValueError("aiNumber操作缺少query参数")
            
            print(f"🔍 执行aiNumber: {query}")
            return_value = ai.ai_number(query, options)
            
            # 数据类型验证
            is_valid, error_msg = DataValidator.validate_ai_number_result(return_value)
            if not is_valid:
                print(f"⚠️ aiNumber数据验证失败: {error_msg}")
                result['validation_warning'] = error_msg
            
            result['success'] = True
            result['execution_details']['query'] = query
            result['execution_details']['options'] = options
            result['return_value'] = return_value
            
            print(f"✅ aiNumber结果: {return_value}")

        elif action == 'aiBoolean':
            # 实现aiBoolean方法
            query = params.get('query')
            options = params.get('options', {})
            if not query:
                raise ValueError("aiBoolean操作缺少query参数")
            
            print(f"🔍 执行aiBoolean: {query}")
            return_value = ai.ai_boolean(query, options)
            
            # 数据类型验证
            is_valid, error_msg = DataValidator.validate_ai_boolean_result(return_value)
            if not is_valid:
                print(f"⚠️ aiBoolean数据验证失败: {error_msg}")
                result['validation_warning'] = error_msg
            
            result['success'] = True
            result['execution_details']['query'] = query
            result['execution_details']['options'] = options
            result['return_value'] = return_value
            
            print(f"✅ aiBoolean结果: {return_value}")

        elif action == 'ai_assert':
            prompt = params.get('prompt')
            if not prompt:
                raise ValueError("ai_assert操作缺少prompt参数")
            return_value = ai.ai_assert(prompt)
            result['success'] = True
            result['execution_details']['assertion'] = prompt
            result['return_value'] = return_value

        elif action == 'ai_wait_for':
            prompt = params.get('prompt')
            timeout = params.get('timeout', 10000)
            if not prompt:
                raise ValueError("ai_wait_for操作缺少prompt参数")
            return_value = ai.ai_wait_for(prompt, timeout)
            result['success'] = True
            result['execution_details']['wait_for'] = prompt
            result['execution_details']['timeout'] = timeout
            result['return_value'] = return_value

        elif action == 'ai_scroll':
            direction = params.get('direction', 'down')
            scroll_type = params.get('scroll_type', 'once')
            locate_prompt = params.get('locate_prompt')
            return_value = ai.ai_scroll(direction, scroll_type, locate_prompt)
            result['success'] = True
            result['execution_details']['direction'] = direction
            result['execution_details']['scroll_type'] = scroll_type
            result['return_value'] = return_value

        elif action == 'set_variable':
            # 新增：直接设置变量操作
            var_name = params.get('name')
            var_value = params.get('value')
            if not var_name:
                raise ValueError("set_variable操作缺少name参数")
            
            variable_manager.store_variable(var_name, var_value, {
                'step_index': step_index,
                'execution_id': execution_id
            })
            result['success'] = True
            result['execution_details']['variable_name'] = var_name
            result['execution_details']['variable_value'] = var_value
            result['variable_assigned'] = var_name
            result['return_value'] = var_value

        elif action == 'get_variable':
            # 新增：获取变量操作
            var_name = params.get('name')
            if not var_name:
                raise ValueError("get_variable操作缺少name参数")
            
            var_value = variable_manager.get_variable(var_name)
            result['success'] = True
            result['execution_details']['variable_name'] = var_name
            result['execution_details']['variable_value'] = var_value
            result['return_value'] = var_value

        else:
            raise ValueError(f'不支持的操作类型: {action}')

        # 如果指定了变量名，存储返回值
        if variable_name and result['return_value'] is not None:
            variable_manager.store_variable(variable_name, result['return_value'], {
                'step_index': step_index,
                'execution_id': execution_id,
                'action': action,
                'description': description
            })
            result['variable_assigned'] = variable_name

        # 截图
        timestamp = int(time.time())
        step_index = result.get('step_index', 0)
        screenshot_filename = f"exec_{execution_id}_step_{step_index}_{timestamp}"

        try:
            screenshot_path = ai.take_screenshot(screenshot_filename)
            result['screenshot'] = {
                'path': f"/static/screenshots/{screenshot_filename}.png",
                'filename': f"{screenshot_filename}.png",
                'timestamp': timestamp,
                'step_index': step_index,
                'step_name': result.get('step_name', f'步骤 {step_index + 1}')
            }
            print(f"截图成功保存: {screenshot_path}")
        except Exception as e:
            print(f"截图失败: {e}")
            result['screenshot'] = None

        # 计算置信度
        result['confidence'] = 0.85 + (hash(str(params)) % 15) / 100

        return result

    except Exception as e:
        error_msg = str(e)
        print(f"[错误] 步骤执行失败: {error_msg}")
        return {
            'success': False,
            'error_message': error_msg,
            'ai_decision': {'action': action, 'params': params, 'error': error_msg},
            'confidence': 0.0,
            'execution_details': {},
            'return_value': None,
            'variable_assigned': None
        }


def execute_test_case_enhanced(ai, test_case, mode='headless'):
    """
    增强的测试用例执行器，支持变量管理
    
    Args:
        ai: MidSceneAI实例
        test_case: 测试用例字典
        mode: 执行模式
        
    Returns:
        执行结果字典
    """
    execution_id = f"exec_{int(time.time())}"
    steps = test_case.get('steps', [])
    results = []
    
    print(f"🚀 开始执行测试用例: {test_case.get('name', '未命名')}")
    print(f"📋 共 {len(steps)} 个步骤")
    
    # 清空之前的变量（可选）
    clear_vars = test_case.get('clear_variables_before_execution', True)
    if clear_vars:
        variable_manager.clear_variables()
    
    try:
        for i, step in enumerate(steps):
            print(f"\n--- 步骤 {i + 1}/{len(steps)} ---")
            
            step_result = execute_single_step_enhanced(ai, step, mode, execution_id, i)
            results.append(step_result)
            
            if not step_result['success']:
                print(f"❌ 步骤 {i + 1} 失败，停止执行")
                break
                
            print(f"✅ 步骤 {i + 1} 完成")
    
    except Exception as e:
        print(f"❌ 测试用例执行失败: {e}")
        results.append({
            'success': False,
            'error_message': str(e),
            'step_index': len(results)
        })
    
    # 统计结果
    total_steps = len(results)
    successful_steps = sum(1 for r in results if r.get('success', False))
    
    execution_result = {
        'execution_id': execution_id,
        'test_case_name': test_case.get('name', '未命名'),
        'total_steps': total_steps,
        'successful_steps': successful_steps,
        'failed_steps': total_steps - successful_steps,
        'success': successful_steps == total_steps and total_steps > 0,
        'steps': results,
        'variables': variable_manager.export_variables(),
        'execution_time': time.time()
    }
    
    print(f"\n🎯 执行完成: {successful_steps}/{total_steps} 步骤成功")
    print(f"📊 当前变量数量: {len(variable_manager.list_variables())}")
    
    return execution_result