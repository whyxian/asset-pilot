"""Pydantic 请求/响应模型

按功能域分文件：
- asset_quote.py:     统一行情模型 AssetQuote
- asset_holding.py:   持仓模型 + 带行情的持仓 HoldingWithQuote
- asset_variety.py:   品种目录模型

ORM 模型在 orm/ 子目录下：
- orm/asset_quote_orm.py:     AssetQuoteRecord
- orm/asset_holding_orm.py:   AssetHoldingRecord
- orm/asset_variety_orm.py:   AssetVarietyRecord
"""
