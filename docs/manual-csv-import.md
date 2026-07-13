# 本地 CSV 导入格式

本方式用于在没有已批准行情 API 时，由人工从允许导出的数据服务获得 CSV 后导入系统。CSV 文件放在本地 `data/` 目录，目录不会纳入 Git。

## 日线行情

必填表头：`trade_date,symbol,open,high,low,close,volume,amount`

```csv
trade_date,symbol,open,high,low,close,volume,amount
2026-07-13,600000,10.00,10.30,9.90,10.20,1200000,12240000
```

- 日期采用 `YYYY-MM-DD`。
- 价格为未复权价格；必须满足 `low <= open/close <= high`。
- 成交量和成交额不得为负数。

## 证券基础信息

必填表头：`symbol,exchange,name,board,active_from`。可选表头：`active_to`。

```csv
symbol,exchange,name,board,active_from,active_to
600000,SSE,浦发银行,main,1999-11-10,
```

## 公告元数据

必填表头：`external_id,published_at,url,title`

```csv
external_id,published_at,url,title
notice-001,2026-07-13T08:00:00+08:00,https://example.test/notice/001,示例公告标题
```

- `published_at` 必须包含时区。
- 系统只保存标题、发布时间、链接、来源和文件行哈希，不保存公告正文。
- 同一来源的 `external_id` 重复导入时不会重复写入。

## 导入边界

- CSV 必须来自你有权使用和导出的来源。
- 不要将账号密码、API Key 或公告全文放入 CSV。
- 每次导入会写入来源健康记录；格式不合格时，系统记录失败状态并返回零条处理结果。
