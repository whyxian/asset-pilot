## 1. 后端暴露起点日期

- [x] 1.1 `OverviewStats` 加 `dietz_start_date: str | None = None`
- [x] 1.2 `overview_service.py` 记录 start_date 到结果

## 2. 前端 Tooltip

- [x] 2.1 概览页历史累计总收益卡片标题旁加 `?` 图标
- [x] 2.2 悬停显示 `format(start_date)-至今`

## 3. 验证

- [x] 3.1 运行 pytest
