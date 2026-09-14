"""MD5签名验证工具（码支付风格）"""
import hashlib
from decimal import Decimal
from typing import Dict, Any
from loguru import logger


def _normalize_value(value: Any) -> str:
    """
    将值统一转换为字符串，用于签名计算
    - 数字类型（int/float/Decimal）保留2位小数
    - 其他类型直接转字符串
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        try:
            return f"{Decimal(str(value)):.2f}"
        except Exception:
            return str(value)
    return str(value)


def generate_sign(params: Dict[str, Any], api_key: str) -> str:
    """
    生成MD5签名
    签名规则：
    1. 过滤sign参数和空值参数
    2. 按参数名ASCII码从小到大排序
    3. 拼接成 key1=value1&key2=value2... 格式（值统一转字符串，数字保留2位小数）
    4. 末尾拼接 &key=api_key
    5. MD5加密，32位小写
    """
    # 过滤空值和sign参数
    filtered = {}
    for k, v in params.items():
        if k == 'sign':
            continue
        if v is None or v == '':
            continue
        filtered[k] = _normalize_value(v)

    # 按ASCII排序
    sorted_keys = sorted(filtered.keys())

    # 拼接
    sign_str = '&'.join([f'{k}={filtered[k]}' for k in sorted_keys])
    sign_str += f'&key={api_key}'

    # MD5加密
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    return sign


def verify_sign(params: Dict[str, Any], api_key: str) -> bool:
    """
    验证签名
    """
    if 'sign' not in params:
        logger.warning("签名验证失败：缺少sign参数")
        return False

    incoming_sign = str(params['sign']).lower()
    generated_sign = generate_sign(params, api_key)

    if incoming_sign == generated_sign:
        return True

    # 日志只输出传入签名的前8位，不泄露完整签名和计算结果
    logger.warning(f"签名验证失败：传入签名={incoming_sign[:8]}***")
    return False


def verify_sign_with_keys(params: Dict[str, Any], api_keys: list) -> bool:
    """
    使用多个API Key验证签名（任一通过即通过）
    """
    for key in api_keys:
        if verify_sign(params, key):
            return True
    return False
