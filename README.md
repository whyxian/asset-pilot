# AssetPilot - 个人投资看板与净值计算器

聚合 A股、美股、加密货币、基金的个人投资看板，支持实时行情、持仓管理、交易记录、净值追踪。

## 技术栈

- **后端**：FastAPI + SQLAlchemy 2.0 (async) + SQLite
- **前端**：React 19 + TypeScript + Vite + TanStack Query + Tailwind CSS
- **定时任务**：APScheduler（行情/汇率后台预热）
- **图表**：Recharts

## 核心功能

1. **概览** — 总市值/成本/盈亏统计卡 + 历史累计总收益（Modified Dietz）+ 资产配比 + 净值走势
2. **持仓** — 品种盈亏列表（实时行情驱动）+ 市场筛选 Tab + 手动刷新
3. **交易** — 交易记录 CRUD + 费率记录 + 市场筛选 Tab
4. **行情** — 四市场实时价格查询（腾讯/新浪/CoinGlass/天天基金）
5. **净值快照** — 组合级 + 品种级双表，历史汇率冻结

## 快速开始

```bash
# 安装依赖
uv venv && source .venv/bin/activate
uv pip install -e backend
uv pip install playwright && playwright install chromium

# 启动后端
uvicorn app.main:app --reload

# 启动前端
cd frontend && npm run dev
```

## 架构

四层分离：`api → services → repositories → data_sources`

- 用户请求只读缓存，后台 APScheduler 定时预热行情(30s) + 汇率(55min)
- 行情五级兜底：内存 → 运行时缓存 → 种子文件 → 硬编码常量
- 汇率五级兜底 + 单飞，永不返回 None
- 交易记录是唯一现金流事实源，recompute 从 0 起点回放反推持仓
- 盈亏率公式统一在 `app/core/formulas.py`，全程 Decimal 运算

## 文档

- [架构设计](docs/architecture.md)
- [需求文档](docs/requirements.md)
- [数据库设计](docs/database.md)
- [开发进度](docs/progress.md)
- [计算公式清单](docs/formulas.md)
- [代码审查 Checklist](docs/code_review/CHECKLIST.md)

## License

MIT
