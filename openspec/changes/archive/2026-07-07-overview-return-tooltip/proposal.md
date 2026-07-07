## Why

历史累计总收益卡片没有说明统计区间，用户无法知道这个收益率是从什么时候开始算的。加一个 info 图标 hover 显示 "YYYY年MM月DD日-至今"。

## What Changes

- `OverviewStats` 加 `dietz_start_date` 字段（Modified Dietz 计算起点日期）
- 前端概览页历史累计总收益卡片加 ? 图标 + Tooltip 显示日期范围

## Capabilities

（微变更，纯 UI 改进，不涉及 spec 修改）

## Impact

- `backend/app/models/overview.py`: +1 字段
- `backend/app/services/overview_service.py`: 记录 start_date
- `frontend/src/features/overview/OverviewPage.tsx`: info 图标 + Tooltip
