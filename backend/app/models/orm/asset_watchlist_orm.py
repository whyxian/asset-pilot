"""自选股 ORM — watchlist

业务语义：
- 独立于 asset_varieties，允许收藏品种表之外的代码（查询成功即可收藏）
- name 为收藏时快照，不依赖品种表存在
- sort_order 预留手动排序（当前默认 0，按创建倒序）
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WatchlistRecord(Base):
    """自选股 — 收藏的标的"""

    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(10), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
