"""安全工具：密码哈希、JWT、加密"""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from cryptography.fernet import Fernet
import base64
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
    to_encode.update({"exp": expire, "type": "refresh"})
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
    """获取Fernet实例，确保key长度正确"""
    key = settings.ENCRYPTION_KEY
    # 如果key不是32字节base64，补全
    key_bytes = key.encode('utf-8')
    if len(key_bytes) < 32:
        key_bytes = key_bytes.ljust(32, b'0')
    elif len(key_bytes) > 32:
        key_bytes = key_bytes[:32]
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_text(plain_text: str) -> str:
    """加密文本"""
    if not plain_text:
        return ""
    f = _get_fernet()
    return f.encrypt(plain_text.encode('utf-8')).decode('utf-8')


def decrypt_text(encrypted_text: str) -> str:
    """解密文本"""
    if not encrypted_text:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(encrypted_text.encode('utf-8')).decode('utf-8')
    except Exception:
        return ""
