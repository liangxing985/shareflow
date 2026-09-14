"""通用Schema"""
from pydantic import BaseModel
from typing import Optional, List, Any, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')


class PageRequest(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PageResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None


class IdResponse(BaseModel):
    id: int
    success: bool = True
