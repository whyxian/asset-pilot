"""开发期一次性脚本：清空持仓 + 交易 + 行情数据（保留 asset_varieties 品种目录）。

使用场景：
- 改了核心算法后，旧赃数据已不一致，开发阶段直接全删重来
- 不影响品种目录（asset_varieties），不需要重新填充

执行方式：
    .venv/bin/python backend/script/clear_dev_data.py

会要求确认（输入 yes）后才真正删除。
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "database" / "assetpilot.db"

TABLES_TO_CLEAR = [
    "transactions",
    "asset_holdings",
    "asset_quote",
    "closed_transactions",  # 如果归档表已建立
    "closed_holdings",
]


def main():
    if not DB_PATH.exists():
        print(f"❌ 数据库不存在：{DB_PATH}")
        return

    print(f"⚠️  即将清空以下表（保留 asset_varieties）：")
    for t in TABLES_TO_CLEAR:
        print(f"    - {t}")
    print(f"\n数据库：{DB_PATH}")
    confirm = input("\n输入 'yes' 确认清空，其它任意输入取消: ").strip()
    if confirm != "yes":
        print("已取消")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN")
        cleared = []
        for tbl in TABLES_TO_CLEAR:
            # 表可能不存在（旧版本数据库还没建归档表）
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
            if not cursor.fetchone():
                continue
            cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            n = cursor.fetchone()[0]
            cursor.execute(f"DELETE FROM {tbl}")
            # 重置自增 id
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{tbl}'")
            cleared.append(f"{tbl} (-{n})")
        conn.commit()
        print(f"\n✅ 已清空：")
        for line in cleared:
            print(f"    {line}")
    except Exception as e:
        conn.rollback()
        print(f"❌ 清空失败已回滚：{e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
