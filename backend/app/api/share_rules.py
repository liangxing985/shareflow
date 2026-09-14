"""分账规则路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.user import User
from app.models.share_rule import ShareRule
from app.schemas.share_rule import ShareRuleCreate, ShareRuleUpdate, ShareRuleResponse
from app.schemas.common import PageResponse
from app.dependencies import get_current_user, require_manager

router = APIRouter(prefix="/share-rules", tags=["分账规则"])


@router.get("", response_model=PageResponse[ShareRuleResponse])
async def list_rules(
    page: int = 1, page_size: int = 20,
    scope_type: str = None, status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """分账规则列表"""
    query = select(ShareRule)
    count_query = select(func.count(ShareRule.id))

    if scope_type:
        query = query.where(ShareRule.scope_type == scope_type)
        count_query = count_query.where(ShareRule.scope_type == scope_type)
    if status:
        query = query.where(ShareRule.status == status)
        count_query = count_query.where(ShareRule.status == status)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(ShareRule.is_default.desc(), ShareRule.priority.desc(), ShareRule.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rules = (await db.execute(query)).scalars().all()

    return PageResponse(items=rules, total=total, page=page, page_size=page_size, total_pages=(total + page_size - 1) // page_size)


@router.get("/{rule_id}", response_model=ShareRuleResponse)
async def get_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """分账规则详情"""
    result = await db.execute(select(ShareRule).where(ShareRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="分账规则不存在")
    return rule


@router.post("", response_model=ShareRuleResponse)
async def create_rule(
    req: ShareRuleCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """创建分账规则"""
    # 校验分账比例合计
    level1_rates = sum(d.rate for d in req.share_details if d.level == 1)
    if level1_rates > 1.0001:
        raise HTTPException(status_code=400, detail=f"一级分账比例合计不能超过100%，当前: {level1_rates*100:.1f}%")

    if req.is_default:
        # 取消其他默认
        result = await db.execute(select(ShareRule).where(ShareRule.is_default == True))
        for r in result.scalars().all():
            r.is_default = False

    rule_data = req.model_dump()
    # Decimal转float，否则JSON字段无法序列化
    rule_data["share_details"] = [
        {**d.model_dump(), "rate": float(d.rate)} for d in req.share_details
    ]

    rule = ShareRule(**rule_data, created_by=current_user.id)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=ShareRuleResponse)
async def update_rule(
    rule_id: int, req: ShareRuleUpdate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """更新分账规则"""
    result = await db.execute(select(ShareRule).where(ShareRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="分账规则不存在")

    update_data = req.model_dump(exclude_unset=True)
    if "share_details" in update_data and update_data["share_details"]:
        level1_rates = sum(d["rate"] for d in update_data["share_details"] if d.get("level", 1) == 1)
        if level1_rates > 1.0001:
            raise HTTPException(status_code=400, detail=f"一级分账比例合计不能超过100%，当前: {level1_rates*100:.1f}%")
        # Decimal转float
        update_data["share_details"] = [
            {**(d if isinstance(d, dict) else d.model_dump()), "rate": float(d["rate"] if isinstance(d, dict) else d.rate)}
            for d in update_data["share_details"]
        ]

    if req.is_default and not rule.is_default:
        result2 = await db.execute(select(ShareRule).where(ShareRule.is_default == True))
        for r in result2.scalars().all():
            r.is_default = False

    for key, value in update_data.items():
        setattr(rule, key, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """删除分账规则（禁用）"""
    result = await db.execute(select(ShareRule).where(ShareRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="分账规则不存在")
    if rule.is_default:
        raise HTTPException(status_code=400, detail="默认规则不能删除，请先设置其他规则为默认")

    rule.status = "inactive"
    await db.commit()
    return {"success": True}


@router.post("/{rule_id}/set-default")
async def set_default(
    rule_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """设为默认规则"""
    result = await db.execute(select(ShareRule).where(ShareRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="分账规则不存在")

    # 取消其他默认
    all_result = await db.execute(select(ShareRule).where(ShareRule.is_default == True))
    for r in all_result.scalars().all():
        r.is_default = False

    rule.is_default = True
    await db.commit()
    return {"success": True}
