"""速率限制工具：登录失败锁定、API限速"""
import time
from collections import defaultdict
from typing import Dict, Tuple
from app.config import settings


# 内存存储（生产环境建议用Redis）
_login_attempts: Dict[str, list] = defaultdict(list)  # key: username_or_ip, value: [timestamp, ...]
_locked_accounts: Dict[str, float] = {}  # key: username_or_ip, value: unlock_timestamp


def check_login_attempts(key: str) -> Tuple[bool, str]:
    """
    检查登录尝试次数
    返回: (是否允许登录, 错误信息)
    """
    now = time.time()

    # 检查是否被锁定
    if key in _locked_accounts:
        if now < _locked_accounts[key]:
            remaining = int((_locked_accounts[key] - now) / 60) + 1
            return False, f"账号已被锁定，请{remaining}分钟后再试"
        else:
            del _locked_accounts[key]
            _login_attempts[key] = []

    return True, ""


def record_login_failure(key: str):
    """记录登录失败"""
    now = time.time()
    _login_attempts[key].append(now)

    # 清理过期记录（只保留最近15分钟）
    cutoff = now - settings.LOGIN_LOCK_MINUTES * 60
    _login_attempts[key] = [t for t in _login_attempts[key] if t > cutoff]

    # 超过最大尝试次数则锁定
    if len(_login_attempts[key]) >= settings.LOGIN_MAX_ATTEMPTS:
        _locked_accounts[key] = now + settings.LOGIN_LOCK_MINUTES * 60
        _login_attempts[key] = []


def clear_login_attempts(key: str):
    """登录成功后清除失败记录"""
    _login_attempts.pop(key, None)
    _locked_accounts.pop(key, None)


# 简单的全局限速（每分钟每IP最多请求数）
_rate_limit_store: Dict[str, list] = defaultdict(list)
RATE_LIMIT_PER_MINUTE = 120  # 每分钟最多120次请求


def check_rate_limit(client_ip: str) -> bool:
    """
    检查全局限速
    返回: True=允许, False=超限
    """
    if not settings.RATE_LIMIT_ENABLED:
        return True

    now = time.time()
    cutoff = now - 60
    _rate_limit_store[client_ip] = [t for t in _rate_limit_store.get(client_ip, []) if t > cutoff]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_PER_MINUTE:
        return False

    _rate_limit_store[client_ip].append(now)
    return True
