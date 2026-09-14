"""分账计算引擎 - 核心业务逻辑"""
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.order import Order
from app.models.share_rule import ShareRule
from app.models.shareholder import Shareholder
from app.models.share_record import ShareRecord
from app.models.share_balance import ShareBalance
from loguru import logger


def to_decimal(value, default="0") -> Decimal:
    """安全转换为Decimal"""
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_money(value: Decimal) -> Decimal:
    """金额四舍五入到分"""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ShareEngine:
    """分账计算引擎"""

    @staticmethod
    async def get_applicable_rule(db: AsyncSession, order: Order) -> Optional[ShareRule]:
        """获取订单适用的分账规则"""
        # 1. 如果订单指定了规则，直接用
        if order.share_rule_id:
            result = await db.execute(select(ShareRule).where(ShareRule.id == order.share_rule_id))
            return result.scalar_one_or_none()

        # 2. 按分类匹配
        if order.category:
            result = await db.execute(
                select(ShareRule)
                .where(
                    ShareRule.scope_type == "category",
                    ShareRule.scope_value == order.category,
                    ShareRule.status == "active"
                )
                .order_by(ShareRule.priority.desc())
            )
            rule = result.scalar_one_or_none()
            if rule:
                return rule

        # 3. 全局默认规则
        result = await db.execute(
            select(ShareRule)
            .where(ShareRule.is_default == True, ShareRule.status == "active")
            .order_by(ShareRule.priority.desc())
        )
        return result.scalar_one_or_none()

    @staticmethod
    def calc_platform_fee(total_amount: Decimal, rule: ShareRule) -> Decimal:
        """计算平台抽成"""
        if rule.platform_fee_fixed and to_decimal(rule.platform_fee_fixed) > 0:
            return round_money(to_decimal(rule.platform_fee_fixed))
        rate = to_decimal(rule.platform_fee_rate, "0.1")
        return round_money(total_amount * rate)

    @staticmethod
    def calc_share_amounts(
        shareable_amount: Decimal,
        share_details: List[Dict],
        shareholders_map: Dict[int, Shareholder]
    ) -> List[Dict]:
        """
        计算各分账方应得金额
        share_details格式: [{"shareholder_id": 1, "rate": 0.6, "level": 1, "parent_id": null}, ...]
        """
        results = []
        level1_total = Decimal("0")
        level1_details = []

        # 第一级：基于可分账金额计算
        for detail in share_details:
            level = detail.get("level", 1)
            if level != 1:
                continue
            shareholder_id = detail["shareholder_id"]
            rate = to_decimal(detail.get("rate", 0))
            amount = round_money(shareable_amount * rate)
            level1_total += amount
            level1_details.append({
                "shareholder_id": shareholder_id,
                "shareholder_name": shareholders_map.get(shareholder_id, Shareholder(name=f"未知({shareholder_id})")).name,
                "rate": rate,
                "share_amount": amount,
                "level": 1,
                "parent_shareholder_id": None,
                "parent_amount": None,
            })

        # 处理尾差：把分账尾差加到第一个一级分账方
        diff = shareable_amount - level1_total
        if abs(diff) >= Decimal("0.01") and level1_details:
            level1_details[0]["share_amount"] = round_money(level1_details[0]["share_amount"] + diff)

        results.extend(level1_details)

        # 第二级及以上：基于上级分账金额计算
        for level in range(2, 10):
            level_details = [d for d in share_details if d.get("level", 1) == level]
            if not level_details:
                break

            # 按parent_id分组
            parent_groups: Dict[int, List[Dict]] = {}
            for detail in level_details:
                parent_id = detail.get("parent_id")
                if parent_id is None:
                    continue
                parent_groups.setdefault(parent_id, []).append(detail)

            for parent_id, group_details in parent_groups.items():
                # 找到上级分账方的金额
                parent_result = next((r for r in results if r["shareholder_id"] == parent_id and r["level"] == level - 1), None)
                if not parent_result:
                    continue
                parent_amount = parent_result["share_amount"]

                level_total = Decimal("0")
                level_results = []
                for detail in group_details:
                    shareholder_id = detail["shareholder_id"]
                    rate = to_decimal(detail.get("rate", 0))
                    amount = round_money(parent_amount * rate)
                    level_total += amount
                    level_results.append({
                        "shareholder_id": shareholder_id,
                        "shareholder_name": shareholders_map.get(shareholder_id, Shareholder(name=f"未知({shareholder_id})")).name,
                        "rate": rate,
                        "share_amount": amount,
                        "level": level,
                        "parent_shareholder_id": parent_id,
                        "parent_amount": parent_amount,
                    })

                # 尾差处理
                diff = parent_amount - level_total
                if abs(diff) >= Decimal("0.01") and level_results:
                    level_results[0]["share_amount"] = round_money(level_results[0]["share_amount"] + diff)

                results.extend(level_results)

        return results

    @staticmethod
    async def execute_share(db: AsyncSession, order: Order, rule: ShareRule, created_by: int = None) -> List[ShareRecord]:
        """执行分账：计算并生成分账明细，更新余额"""
        if order.share_status == "done":
            logger.warning(f"订单 {order.order_no} 已分账，跳过")
            return []

        total_amount = to_decimal(order.total_amount)
        platform_fee = ShareEngine.calc_platform_fee(total_amount, rule)
        shareable_amount = round_money(total_amount - platform_fee)

        # 更新订单
        order.platform_fee = platform_fee
        order.shareable_amount = shareable_amount
        order.share_status = "done"
        order.shared_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

        # 加载分账方信息
        shareholder_ids = [d["shareholder_id"] for d in (rule.share_details or [])]
        shareholders_map = {}
        if shareholder_ids:
            result = await db.execute(select(Shareholder).where(Shareholder.id.in_(shareholder_ids)))
            for sh in result.scalars().all():
                shareholders_map[sh.id] = sh

        # 计算分账金额
        calc_results = ShareEngine.calc_share_amounts(
            shareable_amount,
            rule.share_details or [],
            shareholders_map
        )

        # 生成分账明细并更新余额
        records = []
        for calc in calc_results:
            shareholder = shareholders_map.get(calc["shareholder_id"])
            if shareholder and shareholder.is_blacklisted:
                logger.info(f"分账方 {calc['shareholder_name']} 在黑名单，跳过")
                continue

            record = ShareRecord(
                order_id=order.id,
                order_no=order.order_no,
                shareholder_id=calc["shareholder_id"],
                shareholder_name=calc["shareholder_name"],
                order_amount=total_amount,
                platform_fee=platform_fee,
                shareable_amount=shareable_amount,
                share_rate=calc["rate"],
                share_amount=calc["share_amount"],
                actual_amount=calc["share_amount"],
                level=calc["level"],
                parent_shareholder_id=calc["parent_shareholder_id"],
                parent_amount=calc["parent_amount"],
                status="pending",
            )
            db.add(record)
            records.append(record)

            # 更新余额
            balance_result = await db.execute(
                select(ShareBalance).where(ShareBalance.shareholder_id == calc["shareholder_id"])
            )
            balance = balance_result.scalar_one_or_none()
            if not balance:
                balance = ShareBalance(
                    shareholder_id=calc["shareholder_id"],
                    shareholder_name=calc["shareholder_name"],
                )
                db.add(balance)

            balance.total_receivable = to_decimal(balance.total_receivable) + calc["share_amount"]
            balance.current_balance = to_decimal(balance.current_balance) + calc["share_amount"]
            balance.total_orders = (balance.total_orders or 0) + 1

        await db.flush()
        logger.info(f"订单 {order.order_no} 分账完成，生成 {len(records)} 条明细，平台抽成 {platform_fee}")
        return records
