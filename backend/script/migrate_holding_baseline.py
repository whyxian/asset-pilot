"""一次性迁移脚本：为 asset_holdings 表添加建仓基线字段（initial_quantity / initial_cost_price / initial_total_invested）。

背景：交易记录页 CRUD 上线后，引入"建仓基线 + 全部交易回放"的派生模型。
- initial_* = 用户建仓时填入的初始值，不随交易自动变化
- quantity / cost_price / total_invested = 派生字段，由 initial_* + 全部 transactions 顺序回放得出

迁移逻辑：
1. ALTER TABLE 添加 3 列（带 DEFAULT 0），SQLite 原生支持
2. UPDATE 所有现有行：把当前 quantity / cost_price / total_invested 复制到对应 initial_*
   （首次迁移时还没有交易记录，"现状"就是"基线"）

执行方式：
    .venv/bin/python backend/script/migrate_holding_baseline.py

幂等：自动检测列是否已存在，已存在则跳过加列；UPDATE 也只对 initial_* 仍是 0 的行操作。
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "database" / "assetpilot.db"


def has_column(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """检测某表是否已有指定列"""
    cursor.execute(f"PRAGMA table_info('{table}')")
    return any(row[1] == column for row in cursor.fetchall())


def main():
    if not DB_PATH.exists():
        print(f"❌ 数据库不存在：{DB_PATH}")
        return

    print(f"📂 目标数据库：{DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        "initial_quantity",
        "initial_cost_price",
        "initial_total_invested",
    ]

    try:
        cursor.execute("BEGIN")

        # 步骤 1：检查并添加列
        added = []
        for col in columns_to_add:
            if has_column(cursor, "asset_holdings", col):
                print(f"  ⏭️  {col} 已存在，跳过")
                continue
            cursor.execute(
                f"ALTER TABLE asset_holdings ADD COLUMN {col} NUMERIC(18, 4) NOT NULL DEFAULT 0"
            )
            added.append(col)
            print(f"  ✅ 已添加列 {col}")

        # 步骤 2：把现有 quantity / cost_price / total_invested 同步到 initial_*
        # 仅对 initial_* 仍为 0 的行操作，避免覆盖已有 baseline 数据
        cursor.execute(
            """
            UPDATE asset_holdings
            SET initial_quantity = quantity,
                initial_cost_price = cost_price,
                initial_total_invested = total_invested
            WHERE initial_quantity = 0
              AND initial_cost_price = 0
              AND initial_total_invested = 0
            """
        )
        synced = cursor.rowcount

        conn.commit()
        if added or synced:
            print(f"✅ 迁移完成：新增列 {len(added)} 个，同步 baseline 数据 {synced} 行")
        else:
            print("✅ 无需迁移")
    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败已回滚：{e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
