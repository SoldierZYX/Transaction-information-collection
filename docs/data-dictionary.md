# MVP 数据字典（初稿）

状态：待审阅。所有时间字段存 UTC；业务日期采用 `YYYY-MM-DD` 并以 `Asia/Shanghai` 解释。

## 核心实体

| 实体 | 关键字段 | 约束与用途 |
|---|---|---|
| trading_calendar | date, market, is_trading_day, source_id | `(date, market)` 唯一；决定工作流是否运行 |
| securities | symbol, exchange, name, board, active_from, active_to, source_id | `(symbol, exchange, active_from)` 唯一；保存证券映射与上市状态 |
| market_bars | trade_date, symbol, open, high, low, close, volume, amount, source_id | `(trade_date, symbol, source_id)` 唯一；价格为原始日线口径 |
| index_bars | trade_date, index_code, open, high, low, close, amount, source_id | 标识、日期和来源唯一；市场基准快照 |
| sector_bars | trade_date, sector_code, sector_name, change_pct, amount, source_id | 使用经批准的单一行业分类来源 |
| overseas_quotes | observed_at, instrument, value, currency, market_status, source_id | 保存海外市场上下文及观测时间 |
| raw_records | source_id, external_id, record_type, published_at, url, content_hash, payload_json | `(source_id, external_id)` 或 `(source_id, url, content_hash)` 唯一；原始证据审计 |
| events | event_id, category, direction, importance, freshness, confidence, occurred_at | 由规则或已校验 AI 产生的归并事件 |
| event_evidence | event_id, raw_record_id, relation_type | 事件与原始证据的多对多关联 |
| event_security_links | event_id, symbol, link_basis | 只允许证据或明确规则映射 |
| event_sector_links | event_id, sector_code, link_basis | 只允许证据或明确规则映射 |
| pool_runs | run_id, target_date, rule_version, input_snapshot_hash | 记录股票池输入与规则版本 |
| pool_exclusions | run_id, symbol, reason_code, rule_version | 记录被排除的标的与原因 |
| candidates | candidate_id, run_id, symbol, total_score, confidence, rationale, conditions, invalidation | 每次运行最多输出 5 条观察标的 |
| candidate_scores | candidate_id, component, score, inputs_json, rule_version | 保存可复算的各项评分输入 |
| reports | report_id, run_id, type, target_date, cutoff_at, path, content_hash, status | 保存报告产物及状态 |
| candidate_reviews | report_id, candidate_id, return_close, max_gain, max_drawdown | 仅使用已落库行情进行盘后验证 |
| workflow_runs | run_key, workflow_type, status, started_at, ended_at, failure_stage, force_run | `run_key` 唯一；工作流审计与幂等 |
| delivery_attempts | report_id, delivery_key, status, recipients_hash, retries, forced | `delivery_key` 唯一；防止重复投递 |
| ai_calls | task_name, prompt_version, model, input_record_count, usage_json, status | 记录 AI 成本、输入规模与结果状态 |

## 通用字段规则

- `source_id`：来源准入记录的稳定标识，不能为空。
- `url`：可公开访问的证据链接；对无法公开链接的授权服务，记录服务内稳定标识与授权说明。
- `payload_json`：原始响应的结构化快照，严禁写入密钥、邮箱密码或 SMTP 授权码。
- `content_hash`：使用稳定哈希识别同一内容，辅助精确去重。
- `confidence`：0 至 1 的数值，仅表达证据充分程度，不表达收益概率。
- `status`：采用受控枚举；错误详情另存结构化诊断字段，避免混入敏感信息。

## 数据质量规则

1. 日线满足 `low <= min(open, close) <= max(open, close) <= high`，成交量和成交额不得为负。
2. 证券代码、交易所与名称映射异常时，禁止进入候选评分。
3. 缺失关键行情、证券映射或交易日历时，禁止生成正式观察标的。
4. 每个候选标的必须能追溯到规则输入和至少一个有效来源记录。
