"""
Variables相关API模块（V1版本）
变量建议和管理的API
"""
from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger(__name__)

# 从主蓝图导入
from . import api_bp

@api_bp.route('/v1/executions/<execution_id>/variable-suggestions', methods=['GET'])
def get_variable_suggestions(execution_id):
    """获取变量建议列表（AC-1: 变量建议API）"""
    try:
        from web_gui.services.variable_resolver_service import VariableSuggestionService
        
        # 获取查询参数
        step_index = request.args.get('step_index', type=int)
        include_properties = request.args.get('include_properties', 'true').lower() == 'true'
        limit = request.args.get('limit', type=int)
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 获取变量建议
        result = service.get_variable_suggestions(
            step_index=step_index,
            include_properties=include_properties,
            limit=limit
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"获取变量建议失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/v1/executions/<execution_id>/variables/<variable_name>/properties', methods=['GET'])
def get_variable_properties(execution_id, variable_name):
    """获取变量属性探索信息（AC-2: 对象属性探索API）"""
    try:
        from web_gui.services.variable_resolver_service import VariableSuggestionService
        
        # 获取查询参数
        max_depth = request.args.get('max_depth', 3, type=int)
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 获取变量属性
        result = service.get_variable_properties(variable_name, max_depth=max_depth)
        
        if result is None:
            return jsonify({'error': f'变量 {variable_name} 不存在'}), 404
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"获取变量属性失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/v1/executions/<execution_id>/variable-suggestions/search', methods=['GET'])
def search_variables(execution_id):
    """模糊搜索变量（AC-3: 变量名模糊搜索API）"""
    try:
        from web_gui.services.variable_resolver_service import VariableSuggestionService
        
        # 获取查询参数
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)
        step_index = request.args.get('step_index', type=int)
        
        if not query:
            return jsonify({'error': '搜索查询不能为空'}), 400
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 执行搜索
        result = service.search_variables(query=query, limit=limit, step_index=step_index)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"搜索变量失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/v1/executions/<execution_id>/variables/validate', methods=['POST'])
def validate_variable_references(execution_id):
    """验证变量引用（AC-4: 变量引用验证API）"""
    try:
        from web_gui.services.variable_resolver_service import VariableSuggestionService
        
        # 获取请求数据
        data = request.get_json()
        if not data or 'references' not in data:
            return jsonify({'error': '请提供要验证的变量引用'}), 400
        
        references = data['references']
        step_index = data.get('step_index')
        
        if not isinstance(references, list):
            return jsonify({'error': 'references必须是数组'}), 400
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 验证引用
        result = service.validate_variable_references(references, step_index=step_index)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"变量引用验证失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/v1/executions/<execution_id>/variables/status', methods=['GET'])
def get_variables_status(execution_id):
    """获取变量状态（AC-5: 实时变量状态API）"""
    try:
        from web_gui.services.variable_resolver_service import VariableSuggestionService
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 获取状态信息
        status = service.get_variables_status()
        
        return jsonify({
            'execution_id': execution_id,
            **status
        }), 200
        
    except Exception as e:
        logger.error(f"获取变量状态失败: {str(e)}")
        return jsonify({'error': str(e)}), 500