"""
金山云IAM认证服务
基于AWS V4签名算法实现金山云API认证和Cookie获取
"""

import os
import sys
import base64
import datetime
import hashlib
import hmac
import requests
import json
import logging
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class KsyunAuthService:
    """金山云认证服务类"""
    
    def __init__(self, access_key: str = None, secret_key: str = None, region: str = None):
        """
        初始化金山云认证服务
        
        Args:
            access_key: 访问密钥，如果为None则从环境变量读取
            secret_key: 秘密密钥，如果为None则从环境变量读取  
            region: 区域，如果为None则从环境变量读取
        """
        self.access_key = access_key or os.getenv('KSYUN_ACCESS_KEY')
        self.secret_key = secret_key or os.getenv('KSYUN_SECRET_KEY')
        self.region = region or os.getenv('KSYUN_REGION', 'cn-beijing-6')
        
        if not self.access_key or not self.secret_key:
            raise ValueError("金山云Access Key和Secret Key不能为空，请设置环境变量KSYUN_ACCESS_KEY和KSYUN_SECRET_KEY")
            
        logger.info(f"金山云认证服务初始化成功，区域: {self.region}")
    
    @staticmethod
    def sign(key: bytes, msg: str) -> bytes:
        """HMAC签名"""
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    
    @staticmethod
    def get_signature_key(secret_key: str, date_stamp: str, region: str, service: str) -> bytes:
        """生成签名密钥"""
        k_date = KsyunAuthService.sign(('AWS4' + secret_key).encode('utf-8'), date_stamp)
        k_region = KsyunAuthService.sign(k_date, region)
        k_service = KsyunAuthService.sign(k_region, service)
        k_signing = KsyunAuthService.sign(k_service, 'aws4_request')
        return k_signing
    
    def get_auth_headers(self, service: str, host: str, request_parameters: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
        """
        生成AWS V4签名认证头
        
        Args:
            service: 服务名称 (如 'iam')
            host: 主机名 (如 'iam.cn-beijing-6.api.ksyun.com')
            request_parameters: 请求参数字典
            
        Returns:
            请求URL和认证头字典
        """
        # 创建时间戳
        t = datetime.datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')
        
        # 构建规范请求
        method = 'GET'
        canonical_uri = '/'
        
        # 排序请求参数并URL编码
        sorted_params = sorted(request_parameters.items(), key=lambda d: d[0])
        canonical_querystring = urlencode(sorted_params)
        
        # 构建规范头
        canonical_headers = f'host:{host}\nx-amz-date:{amz_date}\n'
        signed_headers = 'host;x-amz-date'
        
        # 负载哈希(GET请求为空)
        payload_hash = hashlib.sha256(b'').hexdigest()
        
        # 构建规范请求字符串
        canonical_request = f'{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
        
        # 构建签名字符串
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date_stamp}/{self.region}/{service}/aws4_request'
        string_to_sign = f'{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
        
        # 计算签名
        signing_key = self.get_signature_key(self.secret_key, date_stamp, self.region, service)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # 构建授权头
        authorization_header = f'{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
        
        headers = {
            'x-amz-date': amz_date,
            'Authorization': authorization_header,
            'Accept': 'application/json'
        }
        
        endpoint = f'http://{host}'
        request_url = f'{endpoint}?{canonical_querystring}'
        
        return request_url, headers
    
    def make_api_request(self, service: str, host: str, request_parameters: Dict[str, str], timeout: int = 10) -> Optional[Dict]:
        """
        发起API请求
        
        Args:
            service: 服务名称
            host: 主机名
            request_parameters: 请求参数
            timeout: 超时时间（秒）
            
        Returns:
            响应JSON数据或None
        """
        try:
            request_url, headers = self.get_auth_headers(service, host, request_parameters)
            logger.debug(f"请求URL: {request_url}")
            logger.debug(f"请求头: {headers}")
            
            response = requests.get(request_url, headers=headers, timeout=timeout)
            logger.info(f"API请求响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API请求失败: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("API请求超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求异常: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            return None
    
    def get_iam_user_info(self, user_name: str = None) -> Optional[Dict]:
        """
        获取IAM用户信息
        
        Args:
            user_name: 用户名，如果为None则获取当前用户信息
            
        Returns:
            用户信息字典或None
        """
        service = 'iam'
        host = f'iam.{self.region}.api.ksyun.com'
        
        request_parameters = {
            "Action": "GetUser",
            "Version": "2016-03-04"
        }
        
        if user_name:
            request_parameters["UserName"] = user_name
        
        logger.info(f"获取IAM用户信息: {user_name or '当前用户'}")
        response = self.make_api_request(service, host, request_parameters)
        
        if response and response.get('User'):
            logger.info("IAM用户信息获取成功")
            return response['User']
        else:
            logger.error("IAM用户信息获取失败")
            return None
    
    def get_session_token(self) -> Optional[str]:
        """
        获取会话令牌（模拟实现）
        
        在实际场景中，这里应该调用金山云的STS服务获取临时凭证
        目前作为占位符实现，返回基于认证信息生成的会话标识
        
        Returns:
            会话令牌字符串或None
        """
        try:
            # 这里应该调用金山云STS服务获取临时会话令牌
            # 当前使用模拟实现
            user_info = self.get_iam_user_info()
            if user_info:
                # 基于用户信息和当前时间生成会话标识
                timestamp = datetime.datetime.utcnow().timestamp()
                session_data = f"{user_info.get('UserId', 'unknown')}_{timestamp}"
                session_token = base64.b64encode(session_data.encode('utf-8')).decode('utf-8')
                logger.info("会话令牌生成成功")
                return session_token
            else:
                logger.error("无法获取用户信息，会话令牌生成失败")
                return None
        except Exception as e:
            logger.error(f"会话令牌生成失败: {str(e)}")
            return None
    
    def generate_ksyun_cookies(self) -> Optional[Dict[str, str]]:
        """
        生成金山云登录Cookie
        
        基于认证信息生成用于自动登录的Cookie数据
        
        Returns:
            Cookie字典或None
        """
        try:
            logger.info("开始生成金山云登录Cookie")
            
            # 获取用户信息
            user_info = self.get_iam_user_info()
            if not user_info:
                logger.error("无法获取用户信息")
                return None
            
            # 获取会话令牌
            session_token = self.get_session_token()
            if not session_token:
                logger.error("无法获取会话令牌")
                return None
            
            # 构建Cookie数据
            # 注意：这些Cookie名称和值需要根据金山云的实际认证机制调整
            cookies = {
                'ks_session': session_token,
                'ks_user_id': user_info.get('UserId', ''),
                'ks_user_name': user_info.get('UserName', ''),
                'ks_access_key': self.access_key[:8] + '*' * (len(self.access_key) - 8),  # 部分隐藏
                'ks_region': self.region,
                'ks_timestamp': str(int(datetime.datetime.utcnow().timestamp())),
            }
            
            # 生成签名验证Cookie
            cookie_string = '&'.join([f'{k}={v}' for k, v in sorted(cookies.items())])
            cookie_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                cookie_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            cookies['ks_signature'] = cookie_signature
            
            logger.info(f"金山云Cookie生成成功，包含{len(cookies)}个Cookie")
            return cookies
            
        except Exception as e:
            logger.error(f"金山云Cookie生成失败: {str(e)}")
            return None
    
    def validate_credentials(self) -> bool:
        """
        验证认证凭据是否有效
        
        Returns:
            True如果凭据有效，否则False
        """
        try:
            logger.info("验证金山云认证凭据")
            user_info = self.get_iam_user_info()
            if user_info:
                logger.info(f"认证凭据有效，用户: {user_info.get('UserName', 'unknown')}")
                return True
            else:
                logger.error("认证凭据无效")
                return False
        except Exception as e:
            logger.error(f"认证凭据验证失败: {str(e)}")
            return False

# 便捷函数
def get_ksyun_cookies(access_key: str = None, secret_key: str = None, region: str = None) -> Optional[Dict[str, str]]:
    """
    便捷函数：获取金山云登录Cookie
    
    Args:
        access_key: 访问密钥
        secret_key: 秘密密钥
        region: 区域
        
    Returns:
        Cookie字典或None
    """
    try:
        auth_service = KsyunAuthService(access_key, secret_key, region)
        return auth_service.generate_ksyun_cookies()
    except Exception as e:
        logger.error(f"获取金山云Cookie失败: {str(e)}")
        return None

def validate_ksyun_credentials(access_key: str = None, secret_key: str = None, region: str = None) -> bool:
    """
    便捷函数：验证金山云认证凭据
    
    Args:
        access_key: 访问密钥
        secret_key: 秘密密钥
        region: 区域
        
    Returns:
        True如果凭据有效，否则False
    """
    try:
        auth_service = KsyunAuthService(access_key, secret_key, region)
        return auth_service.validate_credentials()
    except Exception as e:
        logger.error(f"验证金山云凭据失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 测试代码
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 测试认证服务
    try:
        auth_service = KsyunAuthService()
        
        # 验证凭据
        if auth_service.validate_credentials():
            print("✅ 认证凭据验证成功")
            
            # 生成Cookie
            cookies = auth_service.generate_ksyun_cookies()
            if cookies:
                print("✅ Cookie生成成功:")
                for name, value in cookies.items():
                    print(f"  {name}: {value}")
            else:
                print("❌ Cookie生成失败")
        else:
            print("❌ 认证凭据验证失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")