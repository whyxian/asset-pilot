"""一次性迁移脚本：为 asset_holdings 表添加 liquidated_at 字段。

- ALTER TABLE 添加列（DATE，可空）
- 把现有 quantity = 0 的行的 liquidated_at 回填为该 ticker 最后一笔 sell 交易的 transaction_date
  （没有 sell 交易就保持 NULL）

执行方式：
    .venv/bin/python backend/script/migrate_holding_liquidated_at.py

幂等：检查列是否已存在，已存在则跳过加列；回填只针对仍为 NULL 的行。
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "database" / "assetpilot.db"


def has_column(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info('{table}')")
    return any(row[1] == column for row in cursor.fetchall())


def main():
    if not DB_PATH.exists():
        print(f"❌ 数据库不存在：{DB_PATH}")
        return

    print(f"📂 目标数据库：{DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN")

        # 步骤 1：加列
        if has_column(cursor, "asset_holdings", "liquidated_at"):
            print("  ⏭️  liquidated_at 已存在，跳过加列")
        else:
            cursor.execute("ALTER TABLE asset_holdings ADD COLUMN liquidated_at DATE")
            print("  ✅ 已添加列 liquidated_at")

        # 步骤 2：回填 quantity=0 且 liquidated_at IS NULL 的记录
        # 取最后一笔 sell（按 transaction_date desc, id desc）
        cursor.execute(
            """
            UPDATE asset_holdings
            SET liquidated_at = (
                SELECT t.transaction_date
                FROM transactions t
                WHERE t.ticker = asset_holdings.ticker AND t.type = 'sell'
                ORDER BY t.transaction_date DESC, t.id DESC
                LIMIT 1
            )
            WHERE quantity = 0 AND liquidated_at IS NULL
            """
        )
        backfilled = cursor.rowcount

        conn.commit()
        if backfilled > 0:
            print(f"✅ 迁移完成：回填 {backfilled} 行清仓日期")
        else:
            print("✅ 迁移完成：无需回填（无 quantity=0 持仓 或 已经处理过）")
    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败已回滚：{e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
