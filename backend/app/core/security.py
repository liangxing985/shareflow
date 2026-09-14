"""安全工具：密码哈希、JWT、加密、密码强度校验"""
import bcrypt
import jwt
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
import base64
import hashlib
from app.config import settings


# ============ 密码哈希 ============

def hash_password(password: str) -> str:
    """哈希密码"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    校验密码强度
    返回: (是否通过, 错误信息)
    要求: 至少8位，包含字母和数字
    """
    if len(password) < 8:
        return False, "密码长度至少8位"
    if not re.search(r'[a-zA-Z]', password):
        return False, "密码必须包含字母"
    if not re.search(r'[0-9]', password):
        return False, "密码必须包含数字"
    return True, ""


# ============ JWT ============

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    # 添加jti用于令牌轮换和撤销
    import uuid
    to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        return None


# ============ 对称加密（用于敏感信息） ============

def _get_fernet() -> Fernet:
    """
    获取Fernet实例
    使用SHA256将用户提供的密钥派生为32字节，再base64编码为Fernet key
    这样无论用户输入什么长度的密钥，都能得到标准的Fernet key
    """
    key = settings.ENCRYPTION_KEY
    if not key:
        raise RuntimeError("ENCRYPTION_KEY 未配置")
    # 用SHA256派生32字节密钥
    key_bytes = hashlib.sha256(key.encode('utf-8')).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_text(plain_text: str) -> str:
    """加密文本"""
    if not plain_text:
        return ""
    try:
        f = _get_fernet()
        return f.encrypt(plain_text.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger = __import__('loguru').logger
        logger.error(f"加密失败: {e}")
        return plain_text  # 加密失败时返回原文，避免数据丢失（生产环境应抛出异常）


def decrypt_text(encrypted_text: str) -> str:
    """解密文本"""
    if not encrypted_text:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(encrypted_text.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        # 不是加密文本，返回原文（兼容旧数据）
        return encrypted_text
    except Exception as e:
        logger = __import__('loguru').logger
        logger.error(f"解密失败: {e}")
        return encrypted_text
