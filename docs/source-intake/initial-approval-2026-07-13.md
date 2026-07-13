# 首批数据源有条件批准记录

状态：项目内有条件批准  
批准日期：2026-07-13  
批准范围：研究与复盘用途，不含自动交易、绕过访问限制或受版权保护正文的批量存储。

## 已批准来源

| 来源 ID | 官方入口 | 批准用途 | 数据保留边界 |
|---|---|---|---|
| SRC-CALENDAR-001 | https://www.sse.com.cn/market/publicdata/；https://www.szse.cn/disclosure/notice/general/ | 交易日、休市安排、市场标识 | 日期、市场、来源链接与采集时间 |
| SRC-SECURITY-001 | https://www.sse.com.cn/assortment/stock/ | 沪市证券代码、简称、板块与状态 | 证券基础字段、来源链接与采集时间 |
| SRC-SECURITY-002 | https://www.szse.cn/market/periodical/ | 深市证券代码、简称、板块与状态 | 证券基础字段、来源链接与采集时间 |
| SRC-DISCLOSURE-001 | https://www.cninfo.com.cn/ | 公告元数据、标题、发布日期与链接 | 元数据、短摘要和链接；不保存全文 |
| SRC-DISCLOSURE-002 | https://www.sse.com.cn/；https://www.szse.cn/disclosure/notice/company/ | 交易所公告元数据、标题、发布日期与链接 | 元数据、短摘要和链接；不保存全文 |
| SRC-POLICY-001 | https://www.csrc.gov.cn/ | 政策监管元数据、标题、发布日期与链接 | 元数据、短摘要和链接；不保存全文 |
| SRC-MANUAL-CSV-001 | 用户从获准服务导出的本地 CSV | 日线行情、证券基础信息、公告元数据 | 结构化字段、来源标识和导入健康记录 |

## 必须遵守的条件

1. 每个适配器上线前，补全对应的数据源准入调查模板，记录具体页面、访问方式、字段、频率、服务条款和 robots 结论。
2. 只使用 HTTPS，采用项目既有的超时、限速、有限重试和来源健康记录机制。
3. 禁止绕过登录、验证码、访问控制、限速或版权保护；不使用未公开、未文档化或需要付费但未授权的接口。
4. 公告和政策仅保存必要元数据、短摘要和链接，不在 MVP 中批量保存全文或解析 PDF。
5. 真实网络访问必须在适配器实现阶段由人工再次确认，并以低频方式运行。

## 未批准范围

- `SRC-MARKET-001` 日线行情、`SRC-NEWS-001` 财经新闻、`SRC-OVERSEAS-001` 海外市场、`SRC-AI-001` AI 仍为待调查状态。
- `SRC-MANUAL-CSV-001` 只允许导入用户已获授权导出的文件，不等同于批准任意网站的自动化访问。
