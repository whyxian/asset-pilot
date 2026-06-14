# backend/script/

运维和入库脚本集合。所有脚本都用项目 `.venv` 的 Python 执行。

> 已归档脚本（早期填充品种目录用的一次性采集脚本）见 [archive/](archive/)。

---

## clear_dev_data.py — 清空开发期赃数据

**用途**：开发期改了核心算法或表结构后，清空 holdings/transactions/closed_*/asset_quote 重新来过。**保留 asset_varieties 品种目录不动**。

```bash
.venv/bin/python backend/script/clear_dev_data.py
```

会要求输入 `yes` 确认。每张表 `DELETE` + 自增 id 重置。

---

## rerun_all_holdings.py — 全量重算所有持仓派生字段

**用途**：当 `recompute_holding` 算法变更（例如把卖出 cost_price 算法从加权平均改为降低成本法）后，DB 里现存持仓的派生字段（`quantity / cost_price / total_invested / liquidated_at`）仍是旧算法的结果。本脚本遍历所有持仓重新计算一遍。

```bash
.venv/bin/python backend/script/rerun_all_holdings.py
```

幂等：再跑一次结果完全相同。

---

## seed_us_variety.py — 从雪球抓单只美股入库

**用途**：新美股 IPO（如 SPCX、CRCL）需要加入 `asset_varieties` 时使用。借助 [test/test_xueqiu.py](backend/test/test_xueqiu.py) 的 Playwright 抓取雪球公司概况页，取 `英文名称` 入库为 `(STOCK, US, ticker)`。

```bash
.venv/bin/python backend/script/seed_us_variety.py SPCX
.venv/bin/python backend/script/seed_us_variety.py SPCX CRCL TSLA   # 批量
```

幂等：已存在的更新 name+is_active；不存在的新增。

依赖：必须先 `playwright install chromium`。

---

## seed_crypto.py — 加密货币品种批量入库

**用途**：把硬编码的加密货币列表（70+ 项主流币种）批量灌进 `asset_varieties`，统一为 `(CRYPTO, CRYPTO, ticker)`。

```bash
.venv/bin/python backend/script/seed_crypto.py
```

幂等：已存在的跳过。
