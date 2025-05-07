from typing import Dict, Any, List, Union, Optional
from uuid import UUID
import json

def convert_uuid_to_str(uuid_bytes: bytes) -> str:
    """将UUID bytes转换为字符串"""
    return str(UUID(bytes=uuid_bytes))

def convert_str_to_uuid_bytes(uuid_str: str) -> bytes:
    """将UUID字符串转换为bytes"""
    try:
        return UUID(uuid_str).bytes
    except ValueError as e:
        raise ValueError(f'Invalid UUID format: {e}')

def parse_image_urls(image_urls: Union[str, List, None]) -> List[str]:
    """解析image_urls字段"""
    if not image_urls:
        return []
    try:
        if isinstance(image_urls, str):
            return json.loads(image_urls)
        return image_urls
    except (json.JSONDecodeError, TypeError):
        return []

def validate_gender(gender: str) -> bool:
    """验证性别字段"""
    return gender in ('male', 'female', 'other')

def validate_response_language(language: str) -> bool:
    """验证响应语言字段"""
    return language in ('chinese', 'english')

def validate_pagination_params(page: Any, page_size: Any) -> tuple[int, int]:
    """验证并规范化分页参数"""
    if not isinstance(page, int) or page < 1:
        page = 1
    if not isinstance(page_size, int) or page_size < 1:
        page_size = 10
    return page, page_size