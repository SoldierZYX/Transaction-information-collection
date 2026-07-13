# MVP 默认配置清单

状态：待审阅。后续工程阶段将把这些默认值实现为环境变量和版本化配置；本文件不包含真实凭据。

| 配置项 | 默认值 | 说明 |
|---|---|---|
| business_timezone | `Asia/Shanghai` | 报告与业务日期时区 |
| storage_timezone | `UTC` | 数据库存储时间时区 |
| premarket_start | `08:45` | 盘前工作流开始时间 |
| premarket_cutoff | `08:55` | 盘前数据截点 |
| premarket_target_send | `09:00` | 盘前目标发送时间 |
| postmarket_start | `17:00` | 盘后工作流开始时间 |
| postmarket_cutoff | `16:55` | 盘后数据截点；数据延迟需显式标注 |
| include_chinext | `false` | 创业板默认关闭 |
| excluded_boards | 科创板、北交所 | 默认不进入股票池 |
| excluded_status | ST、*ST、退市整理、停牌 | 默认排除 |
| min_previous_day_amount_cny | `500000000` | 上一有效交易日最低成交额，单位元 |
| max_candidates | `5` | 观察标的上限，不足不补足 |
| price_adjustment | `raw` | 原始日线价格，不复权 |
| technical_adjustment | `consistent_adjustment` | 技术指标统一使用同一复权口径 |
| database | `SQLite` | MVP 单实例；后续可迁移 PostgreSQL |
| ai_enabled | `false` | 默认关闭，待预算与密钥确认后开启 |
| ai_daily_call_limit | 待定 | 以预算配置限制调用次数 |
| ai_daily_token_limit | 待定 | 以预算配置限制 token 上限 |
| email_enabled | `false` | 默认关闭，待 SMTP 与收件人确认后开启 |
| email_transport | `SMTP` | 支持 SSL 或 STARTTLS，二者互斥 |
| real_network_tests | `false` | 自动测试禁止使用真实网络与真实密钥 |
| scheduling | `manual` | 先连续手动运行 5 个交易日后再调度 |

## 待人工确认

SMTP 服务商与授权码、收件人列表、OpenAI API 预算、获准数据源及其授权范围。
