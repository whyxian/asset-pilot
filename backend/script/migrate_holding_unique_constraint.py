"""一次性迁移脚本：把 asset_holdings.ticker 的 UNIQUE 约束改为 (asset_class, market, ticker) 三元组。

背景：之前 ticker 是单字段 unique，但同 ticker 在不同 market/asset_class 下其实是不同
品种（如 A 股 000001=平安银行 vs 基金 000001=华夏成长）。改用三元组唯一与 asset_varieties
表的约定保持一致。

SQLite 实现：
- ticker 上现有 ix_asset_holdings_ticker 是 UNIQUE INDEX（由 ORM unique=True 生成）
- DROP 它后重建为非 unique 的普通索引
- CREATE 新的复合 UNIQUE INDEX uq_holding_class_market_ticker

执行方式：
    .venv/bin/python backend/script/migrate_holding_unique_constraint.py

幂等：通过 PRAGMA index_list 检查现有索引状态。
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "database" / "assetpilot.db"

OLD_INDEX_NAME = "ix_asset_holdings_ticker"
NEW_UNIQUE_NAME = "uq_holding_class_market_ticker"


def get_index_info(cursor: sqlite3.Cursor) -> dict[str, dict]:
    """获取 asset_holdings 表全部索引的元数据 {name: {unique, columns}}"""
    cursor.execute("PRAGMA index_list('asset_holdings')")
    result = {}
    for _, name, unique, _, _ in cursor.fetchall():
        cursor.execute(f"PRAGMA index_info('{name}')")
        cols = [row[2] for row in cursor.fetchall()]
        result[name] = {"unique": bool(unique), "columns": cols}
    return result


def main():
    if not DB_PATH.exists():
        print(f"❌ 数据库不存在：{DB_PATH}")
        return

    print(f"📂 目标数据库：{DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    indexes = get_index_info(cursor)
    print("当前索引：")
    for name, info in indexes.items():
        flag = "UNIQUE" if info["unique"] else "      "
        print(f"  {flag} {name} ({', '.join(info['columns'])})")

    # 幂等：如果已经有了三元组 unique 索引，且 ticker 不再是 unique → 已迁移过
    has_new_unique = any(
        info["unique"] and info["columns"] == ["asset_class", "market", "ticker"]
        for info in indexes.values()
    )
    ticker_index = indexes.get(OLD_INDEX_NAME)
    if has_new_unique and ticker_index and not ticker_index["unique"]:
        print("\n✅ 已经迁移过，无需重复执行")
        conn.close()
        return

    try:
        cursor.execute("BEGIN")

        # Step 1: 把 ticker 上的 unique index 改为普通索引
        if ticker_index and ticker_index["unique"]:
            cursor.execute(f"DROP INDEX {OLD_INDEX_NAME}")
            cursor.execute(f"CREATE INDEX {OLD_INDEX_NAME} ON asset_holdings (ticker)")
            print(f"\n  ✅ {OLD_INDEX_NAME} 已改为非 unique 索引")
        else:
            print(f"\n  ⏭️  {OLD_INDEX_NAME} 已经不是 unique，跳过")

        # Step 2: 创建三元组 unique 索引
        if not has_new_unique:
            cursor.execute(
                f"CREATE UNIQUE INDEX {NEW_UNIQUE_NAME} "
                f"ON asset_holdings (asset_class, market, ticker)"
            )
            print(f"  ✅ 已创建 UNIQUE INDEX {NEW_UNIQUE_NAME}")

        conn.commit()
        print("\n✅ 迁移完成")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败已回滚：{e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
