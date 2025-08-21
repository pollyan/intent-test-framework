"""
User相关API模块
"""
from flask import Blueprint, request, jsonify

# 从主蓝图导入
from . import api_bp

@api_bp.route('/user/favorites', methods=['GET'])
def get_user_favorites():
    """获取用户收藏的测试用例ID列表"""
    try:
        # 暂时返回模拟数据，实际应该从用户表或缓存中获取
        # 可以通过cookie或session存储
        favorites = [1, 2, 3]  # 模拟收藏的测试用例ID
        
        return jsonify({
            'code': 200,
            'data': favorites
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取收藏列表失败: {str(e)}'
        }), 500

@api_bp.route('/user/favorites/<int:testcase_id>', methods=['POST'])
def add_user_favorite(testcase_id):
    """添加收藏"""
    try:
        # 实际应该保存到数据库或缓存
        return jsonify({
            'code': 200,
            'message': '收藏成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'收藏失败: {str(e)}'
        }), 500

@api_bp.route('/user/favorites/<int:testcase_id>', methods=['DELETE'])
def remove_user_favorite(testcase_id):
    """取消收藏"""
    try:
        # 实际应该从数据库或缓存中删除
        return jsonify({
            'code': 200,
            'message': '取消收藏成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'取消收藏失败: {str(e)}'
        }), 500