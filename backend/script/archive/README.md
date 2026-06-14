# script/archive/

早期填充 `asset_varieties` 品种目录（45,884 条）时用的一次性采集脚本，通过 JSON 中间文件接力。**已完成历史使命，留作参考**。

数据流大致是：

```
fetch_us_stocks.py        → 东方财富 API 抓美股全量列表 → JSON
fetch_us_names.py         → 新浪源批量补英文名 → JSON
convert_ticker_dot.py     → ticker 中 _ 替换为 . → JSON
fetch_cn_fund.py          → akshare 抓基金全量列表 → JSON
merge_etf_fund.py         → 合并 ETF + 普通基金 → JSON
json_tools.py             → 通用 JSON 处理工具（拆分/合并/重命名 key）
seed_varieties.py         → 把整理好的 JSON 批量灌进 asset_varieties 表
```

新增单只品种请用上层 [seed_us_variety.py](../seed_us_variety.py) 或 [seed_crypto.py](../seed_crypto.py)。
