# A股每日交易信息收集与复盘自动化系统

本仓库用于建设一个仅供研究与复盘使用的 Python 系统。系统不接入券商、不自动交易，也不输出交易指令或收益保证。

当前完成 `TASK-001`：建立 MVP 架构决策与数据源准入文档包。该阶段不接入外部网站，不调用付费 API，不包含业务代码。

当前完成 `TASK-002` 的工程基础：Python 包结构、Pydantic 配置模型、控制台日志、测试目录和质量工具配置。真实数据接入、数据库迁移和工作流尚未开始。

当前完成 `TASK-003` 的持久化基础：SQLite 迁移、核心数据表、原始记录与工作流运行审计仓储。相同运行键和来源记录可重复执行而不会重复写入。

当前完成 `TASK-004` 的采集基础：HTTPS 请求策略、超时、限速、有限重试、任务租约锁、来源健康记录和交易日历 mock。此阶段没有接入真实网站。

当前完成 `TASK-005` 的首个数据接入路径：从已获授权的本地 CSV 导入日线行情、证券基础信息和公告元数据。该路径不访问外部网站，重复导入不会重复写入。

当前完成 36Kr 官方 RSS 快讯的执行入口：可将最近窗口内的快讯元数据落入 SQLite，并生成 Markdown 简报；配置 SMTP 后可自动将简报作为邮件附件发送。

## 文档入口

- [架构决策](docs/adr/0001-mvp-architecture.md)
- [数据字典](docs/data-dictionary.md)
- [数据源准入调查模板](docs/source-intake-template.md)
- [首批候选数据源](docs/candidate-sources.md)
- [合规检查清单](docs/compliance-checklist.md)
- [默认配置清单](docs/default-configuration.md)
- [风险登记册](docs/risk-register.md)

## 下一步

完成相关人员对本阶段文档的审阅，并为首批拟接入来源填写准入调查记录；审阅通过后再实现标准化、去重和事件证据关联。

## 本地开发

安装 Python 3.11 或更高版本后，在项目目录执行：

```powershell
py -m pip install -e ".[dev]"
py -m ruff check .
py -m mypy src
py -m pytest
```

将真实凭据仅写入未纳入版本控制的 `.env` 文件；可从 `.env.example` 开始填写。默认关闭 AI 与邮件功能，且自动化测试不得使用真实网络或真实密钥。

## 运行 36Kr 快讯采集

在项目根目录执行以下命令，默认采集最近 24 小时的官方 RSS 快讯，并将简报写入 `reports/`：

```powershell
& "C:/Users/pc/AppData/Local/Programs/Python/Python312/python.exe" -m ashare_review.cli.collect_36kr
```

需要邮件发送时，在未纳入版本控制的 `.env` 中设置 `ASHARE_EMAIL_ENABLED=true`，并填写 SMTP 主机、端口、用户名、授权码与 `ASHARE_SMTP_RECIPIENTS`。多个收件邮箱用英文逗号分隔。
