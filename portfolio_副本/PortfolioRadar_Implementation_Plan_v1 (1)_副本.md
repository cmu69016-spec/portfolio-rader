# PortfolioRadar 实施计划 v1.0
## 面向 AI 开发者的分步指令手册

> **配套文档**：`PortfolioRadar_PRD_v1.1.docx` · `PortfolioRadar_Architecture_v1.md`
> **执行规则**：每一步必须在通过验证测试后，再开始下一步。严禁跨步骤合并实现。

---

## 总览：阶段与时间表

| 阶段 | 内容 | PRD 对应 | 预计耗时 |
|---|---|---|---|
| Phase 0 | 项目骨架搭建 | — | 0.5 天 |
| Phase 1 | 数据接入层 (Datasource) | Week 1–2 | 3 天 |
| Phase 2 | 数据存储层 (Repository + Models) | Week 1–2 | 2 天 |
| Phase 3 | 技术信号引擎 (Model-T) | Week 3–4 | 3 天 |
| Phase 4 | 事件信号引擎 (Model-E + 回测) | Week 5–6 | 4 天 |
| Phase 5 | 情绪信号引擎 (Model-S) | Week 5–6 | 2 天 |
| Phase 6 | 信号聚合 + 建议映射 | Week 7–8 | 2 天 |
| Phase 7 | 日终流水线 + 邮件推送 | Week 7–8 | 2 天 |
| Phase 8 | 周报与模型校准 | Post-MVP | 2 天 |
| Phase 9 | MCP 服务器（可选） | Post-MVP | 1 天 |

---

## Phase 0：项目骨架搭建

### 步骤 0-1：初始化目录结构

**指令**：严格按照 `PortfolioRadar_Architecture_v1.md` 第 2 节描述的目录树，创建以下空目录和占位文件：`app/routers/`、`app/services/`、`app/engines/`、`app/repositories/`、`app/datasources/`、`app/models/`、`app/schemas/`、`app/tasks/`、`app/notifiers/`、`mcp_server/`、`data/keyword_dicts/`、`templates/`、`tests/`。在每个 Python 目录下创建空的 `__init__.py`。在项目根目录创建 `pyproject.toml`，声明项目名称为 `portfolio-radar`、Python 版本 ≥ 3.11，并列出依赖：`akshare`、`tushare`、`sqlalchemy`、`alembic`、`apscheduler`、`pydantic`、`snowlibnlp`（用于情感分析）。在根目录创建 `.env.example`，列出需要配置的环境变量名（不含值）：`TUSHARE_TOKEN`、`SMTP_HOST`、`SMTP_USER`、`SMTP_PASS`、`SMTP_TO`。

**验证测试**：在项目根目录执行 `find . -type f -name "*.py" | sort`，确认所有目录的 `__init__.py` 均存在；执行 `pip install -e .`（或 `uv sync`），确认所有依赖无报错安装完成；执行 `python -c "import akshare, tushare, sqlalchemy, apscheduler, pydantic"` 无任何 ImportError。

---

### 步骤 0-2：创建全局配置模块

**指令**：在 `app/config.py` 中实现一个 `Settings` 类，使用 Pydantic `BaseSettings` 从环境变量（和 `.env` 文件）中自动加载以下配置项：`tushare_token: str`、`smtp_host: str`、`smtp_user: str`、`smtp_pass: str`、`smtp_to: str`、`db_path: str = "data/portfolio_radar.db"`、`weight_tech: float = 0.40`、`weight_event: float = 0.35`、`weight_senti: float = 0.25`、`advice_buy_threshold: float = 0.65`、`advice_sell_threshold: float = 0.35`、`advice_watch_upper: float = 0.55`、`advice_watch_lower: float = 0.45`。将 `Settings` 实例化为模块级别的单例 `settings = Settings()`，供全项目导入。

**验证测试**：在项目根目录创建一个临时 `.env` 文件，填入 `TUSHARE_TOKEN=test_token` 等占位值（不要真实密钥），然后执行 `python -c "from app.config import settings; assert settings.weight_tech + settings.weight_event + settings.weight_senti == 1.0; print('Config OK')"` 输出 `Config OK`；删除临时 `.env` 后确认在没有该文件时 `import` 会因缺少必填字段而抛出 `ValidationError`。

---

## Phase 1：数据接入层

### 步骤 1-1：实现 AKShare 数据源适配器（行情部分）

**指令**：在 `app/datasources/akshare_source.py` 中实现三个函数。

函数一：`fetch_daily_quote(stock_code: str, start_date: str, end_date: str) -> list[dict]`，调用 AKShare 的个股日线行情接口（`ak.stock_zh_a_hist`，复权方式选前复权），返回每日的 `trade_date`、`open`、`high`、`low`、`close`、`volume` 字段，日期格式统一为 `YYYY-MM-DD` 字符串。

函数二：`fetch_money_flow(stock_code: str, date: str) -> dict`，调用 AKShare 的个股资金流向接口（`ak.stock_individual_fund_flow`），返回该日的 `super_net_in`（超大单净流入，单位万元）。若该日无数据（如节假日），返回 `{"super_net_in": 0.0}`。

函数三：`fetch_fund_holdings(fund_code: str) -> list[dict]`，调用 AKShare 的基金重仓股接口（`ak.fund_portfolio_hold_em`），返回前 10 大持仓的 `stock_code`、`weight`（持仓占比，0–1 之间的浮点数）、`report_date`。

**验证测试**：为每个函数写一个独立测试（放在 `tests/test_akshare_source.py`）。测试 1：以 `000001`（平安银行）、起止日期为近 7 个工作日为输入，断言返回列表长度 ≤ 7 且 > 0，每条记录包含所有必须字段，`close` 为正浮点数。测试 2：以 `000001` 和上一个工作日日期为输入，断言返回字典包含 `super_net_in` 且为数字类型。测试 3：以 `161725`（南方煤炭 ETF 联接）为输入，断言返回列表长度 ≤ 10 且 > 0，`weight` 之和 ≤ 1.0。执行 `pytest tests/test_akshare_source.py -v`，三条全部通过。

---

### 步骤 1-2：实现 Tushare 数据源适配器

**指令**：在 `app/datasources/tushare_source.py` 中实现两个函数，均使用从 `app.config.settings` 获取的 `tushare_token` 初始化 Tushare Pro 接口（`ts.pro_api(token)`）。

函数一：`fetch_index_daily(index_code: str, start_date: str, end_date: str) -> list[dict]`，调用 `pro.index_daily`，返回沪深 300（代码 `399300.SZ`）或上证指数的日线数据，字段包括 `trade_date`、`close`，日期格式统一为 `YYYY-MM-DD`。

函数二：`fetch_trade_calendar(start_date: str, end_date: str) -> list[str]`，调用 `pro.trade_cal`，返回指定区间内所有交易日的日期字符串列表（仅 `is_open=1` 的日期），用于在系统内判断某日是否为交易日。

**验证测试**：在 `tests/test_tushare_source.py` 中测试：传入近 30 天日期范围，断言 `fetch_index_daily` 返回列表非空、每条记录 `close > 0`；断言 `fetch_trade_calendar` 返回列表中不包含周六或周日的日期（用 `datetime.weekday()` 校验）。执行 `pytest tests/test_tushare_source.py -v` 全部通过。

---

### 步骤 1-3：实现新闻数据源适配器

**指令**：在 `app/datasources/news_source.py` 中实现一个函数：`fetch_news(date: str) -> list[dict]`，调用 AKShare 的东方财富财经新闻接口（`ak.stock_news_em`）或财经要闻接口，返回该日的新闻列表，每条包含 `title: str`、`source_url: str`（若接口提供）、`publish_time: str`。若接口无法按日期精确过滤，则在函数内按 `date` 参数对结果列表进行后置过滤，只返回 `publish_time` 包含 `date` 字符串的条目。

**验证测试**：在 `tests/test_news_source.py` 中，以最近一个工作日为输入，断言返回列表非空，每条记录的 `title` 字段为非空字符串，`publish_time` 字段包含传入的 `date` 字符串。执行 `pytest tests/test_news_source.py -v` 通过。

---

### 步骤 1-4：实现数据源故障转移（Fallback）

**指令**：在 `app/datasources/fallback.py` 中实现一个装饰器 `with_fallback(fallback_fn)`，接受一个备用函数作为参数。装饰器的作用是：若被装饰函数在执行时抛出任何异常，则自动调用 `fallback_fn` 并传入相同参数，同时向日志（`logging.warning`）记录原始错误信息和「已切换至备用数据源」的提示。在 `app/datasources/akshare_source.py` 的 `fetch_daily_quote` 函数上应用此装饰器，备用函数为调用 Tushare Pro 的 `pro.daily` 接口获取相同数据，并将字段名映射为与 AKShare 返回值相同的格式。

**验证测试**：在 `tests/test_fallback.py` 中，用 `unittest.mock.patch` 模拟 AKShare 接口抛出 `ConnectionError`，调用 `fetch_daily_quote`，断言：函数不抛出异常（降级成功）；返回的数据非空且包含必要字段；警告日志中包含「备用数据源」字样。执行 `pytest tests/test_fallback.py -v` 通过。

---

## Phase 2：数据存储层

### 步骤 2-1：定义 ORM 数据模型

**指令**：在 `app/models/base.py` 中用 SQLAlchemy `DeclarativeBase` 创建全局 `Base` 类和 `engine`（连接字符串从 `app.config.settings.db_path` 读取，使用 SQLite）。然后按照 `PortfolioRadar_Architecture_v1.md` 第 4.2 节的 DDL，在以下文件中创建对应的 SQLAlchemy ORM 模型类：`app/models/fund.py`（`Fund`、`FundHolding`）、`app/models/market.py`（`DailyQuote`、`MoneyFlow`）、`app/models/event.py`（`NewsEvent`）、`app/models/signal.py`（`AggregatedSignal`）、`app/models/backtest.py`（`BacktestSample`）、`app/models/weight.py`（`ModelWeight`）。每个模型类的字段类型和约束须与 DDL 完全一致。在 `app/models/__init__.py` 中导入所有模型类，并提供 `init_db()` 函数，调用 `Base.metadata.create_all(engine)`。

**验证测试**：执行 `python -c "from app.models import init_db; init_db()"` 无报错；执行 `sqlite3 data/portfolio_radar.db ".tables"` 的输出包含以下所有表名：`fund`、`fund_holding`、`daily_quote`、`money_flow`、`news_event`、`aggregated_signal`、`backtest_sample`、`model_weight`；删除 `portfolio_radar.db` 后重新运行，确认幂等（重复执行不报错）。

---

### 步骤 2-2：实现核心 Repository 类

**指令**：在 `app/repositories/base.py` 中定义 `BaseRepository` 基类，持有一个 SQLAlchemy `Session` 实例，提供 `add(obj)`、`get_by_id(model_class, id)`、`bulk_upsert(objs, unique_key)` 三个通用方法，其中 `bulk_upsert` 使用 SQLite 的 `INSERT OR REPLACE` 语义实现。然后实现以下 Repository 类：

`app/repositories/quote_repo.py`：`QuoteRepository`，提供 `upsert_quotes(quotes: list[dict])`（批量写入 `DailyQuote`）和 `get_recent_quotes(stock_code, n_days) -> list[DailyQuote]`（获取最近 N 个交易日行情）。

`app/repositories/event_repo.py`：`EventRepository`，提供 `upsert_event(event: dict)`（写入或更新 `NewsEvent`）和 `get_events_by_group_and_date(keyword_group, start_date, end_date) -> list[NewsEvent]`。

`app/repositories/backtest_repo.py`：`BacktestRepository`，提供 `add_sample(sample: dict)`（写入 `BacktestSample`）、`get_unsettled_samples(keyword_group) -> list[BacktestSample]`（查询 `is_settled=0` 的样本）、`settle_sample(id, excess_return_5d, is_positive)`（回写结算结果）、`get_win_rate(keyword_group, event_type) -> tuple[int, int]`（返回正样本数与总样本数的元组）。

**验证测试**：在 `tests/test_repositories.py` 中：插入 3 条 `DailyQuote`，调用 `get_recent_quotes` 确认返回正确数量；插入同主键 `DailyQuote` 两次，确认数据库中只有 1 条（幂等性）；插入 `BacktestSample` 后调用 `settle_sample`，确认 `is_settled` 变为 1；调用 `get_win_rate`，确认返回元组类型且两个值均为整数。执行 `pytest tests/test_repositories.py -v` 全部通过。

---

## Phase 3：技术信号引擎（Model-T）

### 步骤 3-1：实现量价指标计算函数

**指令**：在 `app/engines/model_t.py` 中实现以下纯函数（不依赖任何外部网络或数据库调用，只接受 Python 原生数据结构作为输入）：

`calc_volume_ratio(quotes: list[dict], n_short=5, n_long=10) -> float`：接受按日期升序排列的行情列表，计算最新一日成交量与过去 5 日均量的比值（量比）。若数据不足 5 条，返回 `1.0`（中性）。

`calc_ma_cross(quotes: list[dict]) -> str`：计算 5 日均线与 20 日均线的位置关系，返回 `"golden"`（5 日均线在 20 日均线上方，即多头排列）、`"dead"`（空头排列）或 `"neutral"`（数据不足或两线近似相等，差值在 0.5% 以内）。

`calc_candle_signal(quote: dict) -> float`：输入单日 OHLC 数据，计算 K 线看多倾向分数（0–1）。阳线（`close > open`）基础分 0.6，阴线基础分 0.4。若上影线长度 > 实体长度的 1.5 倍则减 0.1（上压力大），若下影线长度 > 实体长度的 1.5 倍则加 0.1（有下支撑）。最终分数裁剪到 `[0.0, 1.0]`。

**验证测试**：在 `tests/test_model_t.py` 中，构造已知输入输出的测试用例：连续 5 日量相同时，`calc_volume_ratio` 应返回 `1.0`；构造 5 日均线明确高于 20 日均线的数据，`calc_ma_cross` 返回 `"golden"`；构造一根标准阳线（无影线），`calc_candle_signal` 返回 `0.6`。所有断言使用 `assert abs(result - expected) < 0.01` 形式（浮点容差）。执行 `pytest tests/test_model_t.py::test_technical_indicators -v` 通过。

---

### 步骤 3-2：实现主力资金信号计算函数

**指令**：在 `app/engines/model_t.py` 中继续添加：

`calc_money_flow_signal(super_net_in: float) -> float`：接受超大单净流入金额（万元），返回 0–1 的看多置信度分数。映射规则：净流入 ≥ 50000 万元 → 0.9；10000–50000 → 0.7；0–10000 → 0.55；-10000–0 → 0.45；-50000–-10000 → 0.3；≤ -50000 → 0.1。

`calc_stock_tech_confidence(quotes: list[dict], super_net_in: float) -> float`：组合以上四个指标，加权输出单只个股的技术面看多置信度（0–1）。权重分配：量价信号 `calc_volume_ratio` 权重 30%（> 1.5 视为放量，置信度 0.7；< 0.7 为缩量，置信度 0.35；其余 0.5）、K 线信号权重 20%、均线交叉信号权重 20%（`"golden"` → 0.7，`"dead"` → 0.3，`"neutral"` → 0.5）、资金流信号权重 30%。最终值裁剪到 `[0.0, 1.0]`。

**验证测试**：补充 `tests/test_model_t.py`，测试 `calc_money_flow_signal` 的边界值（传入 100000 得 0.9，传入 -100000 得 0.1）；测试 `calc_stock_tech_confidence`，构造一组「全面看多」场景（放量、阳线、金叉、大幅净流入），断言返回值 ≥ 0.65；构造「全面看空」场景，断言 ≤ 0.35。执行 `pytest tests/test_model_t.py -v` 全部通过。

---

### 步骤 3-3：实现持仓加权聚合（一级聚合）

**指令**：在 `app/engines/model_t.py` 中实现 `calc_fund_tech_confidence(holdings: list[dict], stock_signals: dict[str, float]) -> float`。`holdings` 是基金持仓列表，每条含 `stock_code` 和 `weight`；`stock_signals` 是 `{stock_code: confidence}` 字典。函数按架构文档公式 \(\text{Conf}_{\text{tech}}^{\text{fund}} = \sum w_i \cdot \text{conf}_i / \sum w_i\) 计算持仓加权平均置信度。若某只持仓股的信号不在 `stock_signals` 中，则跳过该股（不参与加权）并记录一条 `logging.warning`。若所有持仓股均无信号数据，返回 `0.5`（中性）。

**验证测试**：测试场景一：两只持仓各占 50%，信号分别为 0.8 和 0.4，期望返回 0.6；测试场景二：三只持仓占比 0.6/0.3/0.1，其中第三只无信号数据，期望返回 `(0.6×signal1 + 0.3×signal2) / 0.9` 的结果；测试场景三：全部持仓无信号，期望返回 0.5，且日志中有 warning。执行 `pytest tests/test_model_t.py::test_fund_aggregation -v` 通过。

---

## Phase 4：事件信号引擎（Model-E + 回测）

### 步骤 4-1：实现关键词词典加载器

**指令**：为每个基金板块在 `data/keyword_dicts/` 目录下创建对应的 YAML 文件，文件名与 PRD 附录中的 `keyword_group` 值一致（如 `coal.yaml`）。YAML 文件结构为：顶层是若干 `event_type` 键，每个键对应一个关键词列表，例如：`mine_closure: [煤矿, 查封, 整顿, 安全事故, 关停]`、`price_rise: [动力煤, 焦煤, 价格上涨, 煤价, 限产]`。至少为以下板块各创建 YAML 文件并填入不少于 3 个 `event_type`、每类不少于 4 个关键词：`coal.yaml`、`semiconductor.yaml`、`nonferrous.yaml`、`chinext.yaml`。在 `app/engines/model_e.py` 中实现 `load_keyword_dicts(dict_dir: str) -> dict`，遍历目录下所有 YAML 文件，返回 `{keyword_group: {event_type: [keywords]}}` 格式的嵌套字典，并缓存（只加载一次）。

**验证测试**：执行 `python -c "from app.engines.model_e import load_keyword_dicts; d = load_keyword_dicts('data/keyword_dicts'); assert 'coal' in d; assert len(d['coal']) >= 3; print('Keywords loaded:', sum(len(v) for kg in d.values() for v in kg.values()), 'total keywords')"` 输出总关键词数 ≥ 48。

---

### 步骤 4-2：实现新闻关键词匹配函数

**指令**：在 `app/engines/model_e.py` 中实现 `match_news_to_events(news_list: list[dict], keyword_dict: dict) -> list[dict]`。遍历 `news_list` 中每条新闻的 `title` 字段，检查是否包含 `keyword_dict` 中任意关键词。若命中，返回命中记录列表，每条包含：`title`（新闻标题）、`keyword_group`（命中的板块名）、`event_type`（命中的事件类型）、`matched_words`（以逗号分隔的命中关键词字符串）。若同一条新闻命中多个 `event_type`，每个均单独记录为一条。重复出现的关键词只记录一次。

**验证测试**：在 `tests/test_model_e.py` 中，构造包含「某煤矿因安全事故被查封」的标题，断言命中 `coal` 的 `mine_closure` 类型；构造不含任何关键词的新闻，断言返回空列表；构造同时含煤炭和半导体关键词的新闻，断言返回两条匹配记录。执行 `pytest tests/test_model_e.py::test_keyword_matching -v` 全部通过。

---

### 步骤 4-3：实现回测引擎

**指令**：在 `app/engines/backtest.py` 中实现两个函数：

`calc_excess_return(sector_code: str, start_date: str, n_days: int, index_code: str = "399300.SZ") -> float | None`：从 `QuoteRepository` 获取板块指数或板块代表 ETF 从 `start_date` 起 `n_days` 个交易日的累计涨幅，减去同期沪深 300 的累计涨幅，得到超额收益。若数据不足 `n_days` 个交易日，返回 `None`（结算条件未成熟）。

`settle_pending_samples(backtest_repo: BacktestRepository, quote_repo: QuoteRepository, trade_calendar: list[str]) -> int`：查询所有 `is_settled=0` 且事件日期距今已满 5 个交易日的 `BacktestSample`，逐条调用 `calc_excess_return` 获取超额收益，回写 `excess_return_5d` 和 `is_positive`（超额收益 > 0 则为 1），更新 `is_settled=1`。返回本次结算的样本数量。

**验证测试**：在 `tests/test_backtest.py` 中，预先在数据库中插入 3 条 `is_settled=0` 的 `BacktestSample`（日期均设为 20 个交易日前），调用 `settle_pending_samples` 后，断言返回值为 3；查询数据库确认 3 条记录的 `is_settled` 均为 1，`is_positive` 字段为 0 或 1（不为 null）。执行 `pytest tests/test_backtest.py -v` 通过。

---

### 步骤 4-4：实现事件置信度计算函数

**指令**：在 `app/engines/model_e.py` 中实现 `calc_event_confidence(matched_events: list[dict], backtest_repo: BacktestRepository) -> tuple[float, int]`。对 `matched_events` 中每个 `(keyword_group, event_type)` 组合，调用 `backtest_repo.get_win_rate` 获取 `(n_positive, n_total)`。将所有命中事件的胜率简单平均作为最终事件置信度，同时返回所有命中事件中最小的 `n_total`（即样本量最少的那类事件的样本数，用于冷启动警告）。若 `matched_events` 为空，返回 `(0.5, 0)`（无事件信号，中性）。若 `n_total == 0`（历史无该类事件样本），该类事件贡献置信度 `0.5`（中性，不影响整体）。

**验证测试**：在数据库中预置若干 `BacktestSample` 样本（10 个正样本 + 5 个负样本），构造一条命中该 `event_type` 的 `matched_events`，断言返回的置信度约为 `10/15 ≈ 0.667`（浮点容差 0.01）；断言返回的 `n_total` 为 15。构造 `matched_events` 为空，断言返回 `(0.5, 0)`。执行 `pytest tests/test_model_e.py::test_event_confidence -v` 通过。

---

## Phase 5：情绪信号引擎（Model-S）

### 步骤 5-1：实现新闻情感打分函数

**指令**：在 `app/engines/model_s.py` 中实现 `calc_news_sentiment(news_list: list[dict], keyword_group: str) -> float`。函数步骤：过滤 `news_list`，只保留标题中包含该 `keyword_group` 对应板块关键词的新闻；对过滤后的每条新闻标题，使用 `SnowNLP(title).sentiments` 获取情感分数（0–1，0 为负面，1 为正面）；将所有分数取平均，即为该板块的情绪置信度。若过滤后新闻列表为空，返回 `0.5`（中性）。

**验证测试**：在 `tests/test_model_s.py` 中，构造一组明显正面新闻标题（如「煤炭产量大增，价格屡创新高」），断言返回值 > 0.55；构造一组明显负面标题（如「煤矿事故频发，监管趋严整顿」），断言返回值 < 0.45；传入空列表，断言返回 0.5。执行 `pytest tests/test_model_s.py -v` 全部通过。

---

## Phase 6：信号聚合与建议映射

### 步骤 6-1：实现二级加权聚合

**指令**：在 `app/engines/aggregator.py` 中实现 `calc_final_confidence(conf_tech: float, conf_event: float, conf_senti: float, weight_tech: float, weight_event: float, weight_senti: float) -> float`，按架构文档的公式计算三模型加权综合置信度，裁剪到 `[0.0, 1.0]`。在同一文件中实现 `get_current_weights(weight_repo) -> tuple[float, float, float]`，查询 `ModelWeight` 表中最新一条记录，返回三个权重；若表为空，返回配置文件的默认初始值（0.40 / 0.35 / 0.25）。

**验证测试**：断言三权重之和始终为 1.0（传入 0.4/0.35/0.25）；断言传入三个相同置信度 0.6 时，返回值也为 0.6；断言结果被裁剪（即便加权后超过 1.0 也不超出范围）。执行 `pytest tests/test_aggregator.py -v` 通过。

---

### 步骤 6-2：实现建议映射函数

**指令**：在 `app/engines/advice.py` 中实现 `map_to_advice(conf_final: float) -> dict`，按 PRD 3.2.4 节的置信度区间表，返回包含以下字段的字典：`advice`（字符串 `"BUY"` / `"HOLD"` / `"SELL"` / `"WATCH"`）、`color`（`"green"` / `"yellow"` / `"red"` / `"orange"`）、`label_zh`（中文建议标签：`"建议买入"` / `"建议持有"` / `"建议卖出"` / `"持有，关注次日信号"`）。

**验证测试**：覆盖所有边界值：传入 `0.65` 得 `BUY`；传入 `0.64` 得 `WATCH`；传入 `0.55` 得 `WATCH`；传入 `0.54` 得 `HOLD`；传入 `0.45` 得 `HOLD`；传入 `0.44` 得 `WATCH`；传入 `0.35` 得 `WATCH`；传入 `0.34` 得 `SELL`。执行 `pytest tests/test_advice.py -v` 全部通过。

---

## Phase 7：日终流水线与邮件推送

### 步骤 7-1：实现日终流水线服务

**指令**：在 `app/services/pipeline_service.py` 中实现 `run_daily_pipeline(trade_date: str) -> list[dict]`。该函数编排以下步骤（按顺序调用各层，不直接调用任何外部 API）：

1. 从数据库读取所有已配置的基金列表及其最新持仓数据。
2. 对每只持仓个股，调用 Datasource 层拉取当日日线行情和资金流向数据，写入数据库（通过 Repository 层）。
3. 拉取当日和前一日的财经新闻，写入数据库。
4. 对每只基金，调用 `signal_service.compute_fund_signal(fund_code, trade_date)` 计算三模型置信度和综合置信度。
5. 将综合信号结果写入 `aggregated_signal` 表。
6. 调用 `backtest_service.settle_pending(trade_date)` 结算到期的回测样本。
7. 返回所有基金的信号结果列表（用于报告生成）。

函数须在顶部记录开始日志，在底部记录「流水线完成，共处理 N 只基金」的日志。

**验证测试**：在 `tests/test_pipeline.py` 中，用 `unittest.mock.patch` 将所有 Datasource 层函数替换为返回预设固定数据的 Mock，调用 `run_daily_pipeline("2026-06-06")`，断言返回列表长度等于预置基金数量；断言 `aggregated_signal` 表中对应日期的记录数与基金数量一致；断言所有记录的 `advice` 字段为合法值（`BUY/HOLD/SELL/WATCH`）。执行 `pytest tests/test_pipeline.py -v` 通过。

---

### 步骤 7-2：实现 HTML 日报模板

**指令**：在 `templates/daily_report.html` 中创建一个 Jinja2 HTML 模板，渲染 PRD 3.2.5 节描述的日报结构。模板需包含以下变量槽：`{{ report_date }}`（日期）、`{{ fund_name }}`（基金名称）、`{{ fund_code }}`（基金代码）、`{{ advice_label_zh }}`（中文建议）、`{{ advice_color }}`（用于色块显示）、`{{ conf_final_pct }}`（综合置信度百分比）、`{{ conf_tech_pct }}`、`{{ conf_event_pct }}`、`{{ conf_senti_pct }}`（各模型置信度）、`{{ weight_tech_pct }}`、`{{ weight_event_pct }}`、`{{ weight_senti_pct }}`（权重百分比）、`{{ event_hit_count }}`（历史命中次数）、`{{ is_low_confidence }}`（冷启动警告布尔值）、`{{ historical_accuracy }}`（过去 30 日胜率）。样式要求：纯 inline CSS，兼容主流邮件客户端，不使用外部字体或 JavaScript。

**验证测试**：在 `tests/test_report.py` 中，构造一个包含所有变量的测试字典，用 Jinja2 渲染模板，断言：渲染结果为合法 HTML 字符串（长度 > 500 字符）；断言字符串中包含测试字典中的 `fund_name` 值；断言当 `is_low_confidence=True` 时，渲染结果包含「低置信度」或「样本不足」字样。执行 `pytest tests/test_report.py::test_template_rendering -v` 通过。

---

### 步骤 7-3：实现邮件推送器

**指令**：在 `app/notifiers/email_notifier.py` 中实现 `send_daily_report(html_content: str, subject: str) -> bool`，使用 Python 标准库 `smtplib` 和 `email` 模块，通过 `app.config.settings` 中的 SMTP 配置发送 HTML 格式邮件。发送成功返回 `True`，任何异常均 `logging.error` 记录后返回 `False`（不向上抛出异常，避免推送失败中断整条流水线）。邮件编码使用 UTF-8，`Content-Type` 为 `text/html`。

**验证测试**：在 `tests/test_notifier.py` 中，用 `unittest.mock.patch("smtplib.SMTP")` Mock SMTP 对象，调用 `send_daily_report("<h1>测试</h1>", "测试日报")`，断言返回 `True`；断言 Mock 的 `sendmail` 方法被调用且第一个参数为 `settings.smtp_user`；再次测试当 SMTP 连接抛出异常时，函数返回 `False` 且不抛出异常。执行 `pytest tests/test_notifier.py -v` 通过。

---

### 步骤 7-4：接入定时任务调度器

**指令**：在 `app/tasks/scheduler.py` 中使用 APScheduler 的 `BackgroundScheduler` 注册两个定时任务：任务一：每个工作日（周一至周五）16:00 触发，调用 `pipeline_service.run_daily_pipeline`，并将流水线结果传递给 `report_service.build_daily_report`，最后调用 `email_notifier.send_daily_report` 发送。任务二：每周五 17:00 触发，调用 `calibration_service.run_weekly_calibration`（此服务在 Phase 8 实现，当前可注册占位）。在 `app/tasks/daily_job.py` 中实现 `run()`，作为任务一的入口函数，负责获取当日交易日历、判断今日是否为交易日（非交易日直接返回，记录 `logging.info`），再调用流水线。提供 `python -m app.tasks.scheduler` 入口，使调度器可独立启动（`start()` + 阻塞主线程）。

**验证测试**：执行 `python -m app.tasks.scheduler &`，等待 3 秒后检查进程是否仍在运行（未崩溃）；在代码中临时将定时任务触发时间改为「当前时间 +10 秒」，运行后确认控制台在 10 秒内出现「开始运行日终流水线」的日志输出；杀掉进程，检查日志文件中无未捕获的异常堆栈。

---

## Phase 8：周报与模型校准

### 步骤 8-1：实现周度准确率计算

**指令**：在 `app/services/calibration_service.py` 中实现 `calc_weekly_accuracy(fund_code: str, week_start: str, week_end: str) -> dict`。该函数从 `aggregated_signal` 表查询指定周期内的所有日报信号，对每条信号记录，查询发出信号后 1–3 个交易日内基金净值的实际走势（通过 `QuoteRepository` 获取基金对应的主仓个股加权涨跌幅近似）。若信号为 `BUY` 或 `HOLD` 而实际上涨，判定为命中；若信号为 `SELL` 而实际下跌，判定为命中。返回 `{fund_code, n_correct, n_total, accuracy, model_breakdown: {tech_acc, event_acc, senti_acc}}`，其中 `model_breakdown` 单独计算每个模型作为主要信号时的准确率。

**验证测试**：预置一周（5 个交易日）的 `aggregated_signal` 记录和对应的行情数据，其中 3 条信号方向与实际走势一致，调用 `calc_weekly_accuracy`，断言 `n_total=5`、`n_correct=3`、`accuracy=0.6`（浮点容差 0.01）。执行 `pytest tests/test_calibration.py::test_accuracy_calc -v` 通过。

---

### 步骤 8-2：实现权重自动校准

**指令**：在 `app/services/calibration_service.py` 中实现 `run_weekly_calibration() -> dict`，在每次执行时：查询过去 2 周所有基金的 `model_breakdown` 准确率；若某模型连续 2 周准确率 < 40%，将其权重降低 5%（最低不低于 10%），等比例提升其他两模型权重，确保三权重之和始终为 1.0，并记录调整原因文字说明；将新权重和原因写入 `model_weight` 表（新增一条记录，`week_start` 为当前周一日期）；返回调整结果摘要字典（包含新旧权重对比和触发条件说明）。若无需调整，写入一条与上周相同的权重记录（表明系统仍在正常运行），并注明「本周无需调整」。

**验证测试**：预置连续 2 周某模型准确率均为 35% 的历史数据，调用 `run_weekly_calibration()`，断言：`model_weight` 表新增一条记录；新记录中该模型权重比上周减少 0.05；三个新权重之和仍为 1.0（浮点容差 0.001）；返回字典中 `reason` 字段包含该模型名称。执行 `pytest tests/test_calibration.py -v` 全部通过。

---

## Phase 9：MCP 服务器（商业化阶段）

### 步骤 9-1：实现 MCP 工具接口

**指令**：在 `mcp_server/tools.py` 中实现以下三个函数作为 MCP 工具，每个函数的输入输出均为可 JSON 序列化的原生 Python 类型：

`get_fund_signal(fund_code: str, date: str) -> dict`：调用 `signal_repo.get_signal_by_date(fund_code, date)`，返回该基金当日的完整信号构成，包括三模型置信度、权重快照、综合置信度、建议文字、历史命中次数、是否为低置信度（样本不足警告）。

`explain_event_history(keyword_group: str, event_type: str) -> dict`：调用 `backtest_repo.get_win_rate` 并查询最近 10 条已结算样本的事件日期与超额收益，返回胜率、总样本数、最近 10 次事件的超额收益列表。

`get_holding_detail(fund_code: str) -> list[dict]`：调用 `fund_repo.get_latest_holdings(fund_code)`，返回最新持仓 Top10 的股票代码、名称、持仓比例、最新单日技术信号置信度。

**验证测试**：在 `tests/test_mcp_tools.py` 中，为每个函数预置数据库数据，调用函数，断言返回值可被 `json.dumps()` 序列化且无异常；断言关键字段存在且值合理（如 `conf_final` 在 0–1 之间）；断言当传入不存在的 `fund_code` 时，函数返回 `{"error": "fund not found"}` 而非抛出异常。执行 `pytest tests/test_mcp_tools.py -v` 全部通过。

---

### 步骤 9-2：注册 MCP 服务器

**指令**：在 `mcp_server/server.py` 中，使用 MCP Python SDK（`mcp`）将 `mcp_server/tools.py` 中的三个函数注册为 MCP 工具，工具名称分别为 `get_fund_signal`、`explain_event_history`、`get_holding_detail`，并为每个工具提供中英文双语描述字符串。提供 `python -m mcp_server.server` 入口，启动 MCP 服务器（stdio 模式）。在项目根目录创建 `mcp_config.json`（Claude Desktop 可直接使用的配置文件），写入服务器名称、启动命令和工作目录。

**验证测试**：执行 `python -m mcp_server.server`，确认进程正常启动且无启动报错（等待 3 秒后进程仍运行）；使用 MCP Inspector 或 `mcp dev` 命令连接服务器，调用 `get_fund_signal`，确认返回合法 JSON 响应；将 `mcp_config.json` 配置加入 Claude Desktop，确认 PortfolioRadar 工具出现在工具列表中，调用后返回真实数据。

---

## 附录：整体测试验收标准

在所有 Phase 完成后，执行以下端到端验收：

**验收测试 E2E-1（流水线完整性）**：在真实环境（含有效 Tushare token 和真实基金代码）下，手动调用 `pipeline_service.run_daily_pipeline` 传入最近一个交易日，确认：流水线在 5 分钟内完成；`aggregated_signal` 表中有该日记录；`advice` 字段为合法值；控制台无 ERROR 级别日志。

**验收测试 E2E-2（邮件推送）**：配置真实 SMTP 后，触发完整流水线，确认在流水线结束后 3 分钟内收到 HTML 格式邮件；邮件内容包含基金名称、综合置信度百分比、中文建议标签三项关键信息。

**验收测试 E2E-3（回测结算）**：手动向 `backtest_sample` 插入 3 条 `is_settled=0` 且日期为 10 个交易日前的记录，调用 `settle_pending_samples`，确认 3 条记录全部被结算（`is_settled=1`）且 `excess_return_5d` 字段为数字（非 null）。

**验收测试 E2E-4（冷启动警告）**：对一个从未命中过任何事件的板块，触发流水线，确认日报中出现「低置信度（样本不足）」字样，且建议仍然输出（不因样本不足而崩溃）。
