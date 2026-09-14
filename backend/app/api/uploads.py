"""文件上传路由"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.dependencies import get_current_user
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/uploads", tags=["文件上传"])

# 允许的图片类型
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}

# 允许的文件类型（对账单等）
ALLOWED_FILE_TYPES = {
    **ALLOWED_IMAGE_TYPES,
    "application/pdf": ".pdf",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/csv": ".csv",
}


def ensure_upload_dir():
    """确保上传目录存在"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


def generate_filename(original_filename: str, content_type: str) -> str:
    """生成安全的文件名"""
    ext = ALLOWED_FILE_TYPES.get(content_type, "")
    if not ext:
        # 从原文件名获取扩展名
        _, ext = os.path.splitext(original_filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = uuid.uuid4().hex[:8]
    return f"{timestamp}_{random_str}{ext}"


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """上传图片（收款码、凭证等）"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的图片类型: {file.content_type}，支持: jpg/png/gif/webp")

    # 检查文件大小
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制: {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB")

    ensure_upload_dir()
    filename = generate_filename(file.filename, file.content_type)
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    # 返回可访问的URL
    return {
        "url": f"/uploads/{filename}",
        "filename": filename,
        "size": len(contents),
        "content_type": file.content_type,
    }


@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """上传通用文件（对账单、Excel等）"""
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}")

    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制: {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB")

    ensure_upload_dir()
    filename = generate_filename(file.filename, file.content_type)
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    return {
        "url": f"/uploads/{filename}",
        "filename": filename,
        "original_filename": file.filename,
        "size": len(contents),
        "content_type": file.content_type,
    }
