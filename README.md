# A股每日交易信息收集与复盘自动化系统

本仓库用于建设一个仅供研究与复盘使用的 Python 系统。系统不接入券商、不自动交易，也不输出交易指令或收益保证。

当前完成 `TASK-001`：建立 MVP 架构决策与数据源准入文档包。该阶段不接入外部网站，不调用付费 API，不包含业务代码。

## 文档入口

- [架构决策](docs/adr/0001-mvp-architecture.md)
- [数据字典](docs/data-dictionary.md)
- [数据源准入调查模板](docs/source-intake-template.md)
- [首批候选数据源](docs/candidate-sources.md)
- [合规检查清单](docs/compliance-checklist.md)
- [默认配置清单](docs/default-configuration.md)
- [风险登记册](docs/risk-register.md)

## 下一步

完成相关人员对本阶段文档的审阅，并为首批拟接入来源填写准入调查记录；审阅通过后再初始化 Python 工程基础。
