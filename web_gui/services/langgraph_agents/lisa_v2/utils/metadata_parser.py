"""
LLM 响应元数据解析器

从混合输出格式中提取 JSON 元数据块
"""

import json
import re
from typing import Dict, Optional


def extract_metadata(response: str) -> Dict:
    """
    从混合响应中提取 JSON 元数据
    
    混合输出格式：
    ```
    [Lisa 的自然语言响应内容...]
    
    ---
    ```json
    {
      "gate_status": "pass" | "stay",
      "output_summary": "...",
      "next_action": "..."
    }
    ```
    ```
    
    Args:
        response: LLM 的完整响应
        
    Returns:
        解析后的元数据字典，如果解析失败返回空字典
    """
    if not response:
        return {}
    
    try:
        # 查找 JSON 代码块
        # 支持 ```json 和 ``` 两种格式
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, response)
        
        if matches:
            # 取最后一个 JSON 块（通常元数据在末尾）
            json_str = matches[-1].strip()
            return json.loads(json_str)
        
        # 备选：查找裸 JSON 对象（以 { 开头，} 结尾）
        json_obj_pattern = r'\{[^{}]*"gate_status"[^{}]*\}'
        obj_matches = re.findall(json_obj_pattern, response)
        
        if obj_matches:
            return json.loads(obj_matches[-1])
            
    except json.JSONDecodeError:
        pass
    except Exception:
        pass
    
    return {}


def extract_gate_status(response: str) -> Optional[str]:
    """
    快捷方法：仅提取 gate_status
    
    Args:
        response: LLM 的完整响应
        
    Returns:
        "pass" | "stay" | None
    """
    metadata = extract_metadata(response)
    return metadata.get("gate_status")


def extract_natural_response(response: str) -> str:
    """
    从混合响应中提取自然语言部分（移除 JSON 元数据）
    
    Args:
        response: LLM 的完整响应
        
    Returns:
        纯自然语言响应
    """
    if not response:
        return ""
    
    # 移除末尾的 JSON 代码块
    # 查找最后一个 --- 分隔符之前的内容
    parts = response.rsplit("---", 1)
    
    if len(parts) > 1:
        # 检查分隔符后面是否包含 JSON
        after_separator = parts[1]
        if "```json" in after_separator or '"gate_status"' in after_separator:
            return parts[0].strip()
    
    # 如果没有分隔符，尝试移除末尾的 JSON 块
    json_pattern = r'\s*```json\s*[\s\S]*?```\s*$'
    cleaned = re.sub(json_pattern, '', response)
    
    return cleaned.strip()

