"""一次性迁移脚本：为 asset_quote 表加上 UNIQUE(ticker, timestamp) 约束。

SQLite 不支持直接 ALTER TABLE ADD CONSTRAINT，需要走「建临时表 → 迁数据 → 替换」的标准流程：
1. 找出 (ticker, timestamp) 重复的记录，每组保留 id 最大的（最新写入）
2. 创建带 UNIQUE 约束的新表 asset_quote_new
3. 把去重后的数据迁过去
4. DROP 旧表，RENAME 新表

执行方式：
    .venv/bin/python backend/script/migrate_asset_quote_unique.py

幂等：如果约束已存在，脚本会自动检测并退出，不会重复迁移。
"""

import sqlite3
from pathlib import Path

# 数据库路径（项目根 / data/database/assetpilot.db）
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "database" / "assetpilot.db"


def has_unique_constraint(cursor: sqlite3.Cursor) -> bool:
    """检测 asset_quote 表是否已经存在 (ticker, timestamp) 的 UNIQUE 索引"""
    cursor.execute("PRAGMA index_list('asset_quote')")
    indexes = cursor.fetchall()  # (seq, name, unique, origin, partial)
    for _, name, unique, _, _ in indexes:
        if not unique:
            continue
        cursor.execute(f"PRAGMA index_info('{name}')")
        cols = [row[2] for row in cursor.fetchall()]  # row = (seqno, cid, name)
        if cols == ["ticker", "timestamp"] or cols == ["timestamp", "ticker"]:
            return True
    return False


def main():
    if not DB_PATH.exists():
        print(f"❌ 数据库不存在：{DB_PATH}")
        return

    print(f"📂 目标数据库：{DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 幂等检查
    if has_unique_constraint(cursor):
        print("✅ asset_quote 已存在 UNIQUE(ticker, timestamp)，无需迁移")
        conn.close()
        return

    # 统计当前行数 + 重复组数
    cursor.execute("SELECT COUNT(*) FROM asset_quote")
    total = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM (SELECT ticker, timestamp FROM asset_quote "
        "GROUP BY ticker, timestamp HAVING COUNT(*) > 1)"
    )
    dup_groups = cursor.fetchone()[0]
    print(f"📊 当前行数 {total}，重复 (ticker, timestamp) 组数 {dup_groups}")

    try:
        cursor.execute("BEGIN")

        # 创建带 UNIQUE 约束的新表（结构对齐 ORM）
        cursor.execute(
            """
            CREATE TABLE asset_quote_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker VARCHAR(30) NOT NULL,
                market VARCHAR(10) NOT NULL,
                name VARCHAR(200) DEFAULT '',
                price NUMERIC(18, 4) NOT NULL,
                currency VARCHAR(3) DEFAULT 'USD',
                change_price NUMERIC(18, 4),
                change_ratio FLOAT,
                timestamp DATETIME NOT NULL,
                source VARCHAR(30) DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                created_by VARCHAR(100),
                updated_by VARCHAR(100),
                CONSTRAINT uq_quote_ticker_timestamp UNIQUE (ticker, timestamp)
            )
            """
        )

        # 去重迁移：每组 (ticker, timestamp) 保留 id 最大的那条
        cursor.execute(
            """
            INSERT INTO asset_quote_new
            SELECT * FROM asset_quote WHERE id IN (
                SELECT MAX(id) FROM asset_quote GROUP BY ticker, timestamp
            )
            """
        )
        migrated = cursor.rowcount

        # DROP 旧表，RENAME 新表
        cursor.execute("DROP TABLE asset_quote")
        cursor.execute("ALTER TABLE asset_quote_new RENAME TO asset_quote")

        # 重建 ticker 索引（ORM 上 ticker 是 index=True）
        cursor.execute("CREATE INDEX ix_asset_quote_ticker ON asset_quote (ticker)")

        conn.commit()
        print(f"✅ 迁移完成：保留 {migrated} 行，丢弃 {total - migrated} 行重复数据")
    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败已回滚：{e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
