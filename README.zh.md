<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/payroll-engine/readme.png" alt="Payroll Engine logo" width="400">
</p>

<h1 align="center">Payroll Engine</h1>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/payroll-engine/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/payroll-engine/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/payroll-engine/"><img src="https://img.shields.io/pypi/v/payroll-engine" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/payroll-engine/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

**一个以库为核心的 PSP 系统，用于工资发放和受监管的资金流动。**

确定性追加只读账本。明确的资金注入机制。可重放的事件。仅提供建议的 AI（默认禁用）。强调正确性而非便利性。

## 信任锚点

在采用此库之前，请务必查看：

| 文档 | 目的 |
| ---------- | --------- |
| [docs/psp_invariants.md](docs/psp_invariants.md) | 系统不变性（保证的内容） |
| [docs/threat_model.md](docs/threat_model.md) | 安全分析 |
| [docs/public_api.md](docs/public_api.md) | 公共 API 接口规范 |
| [docs/compat.md](docs/compat.md) | 兼容性保证 |
| [docs/adoption_kit.md](docs/adoption_kit.md) | 评估和集成指南 |

*我们知道这涉及到资金流动。这些文档证明我们对此非常重视。*

---

## 存在的原因

大多数工资系统将资金流动视为次要问题。他们会调用一个支付 API，希望一切顺利，并在出现故障时进行补救。这会导致：

- **静默失败：** 支付会消失得无影无踪。
- **对账噩梦：** 银行对账单与记录不符。
- **责任混乱：** 如果出现退款，谁来支付？
- **审计漏洞：** 无法追踪实际发生了什么。

该项目通过将资金流动视为首要关注点，并采用适当的金融工程方法来解决这些问题。

## 核心原则

### 为什么追加只读账本很重要

你无法撤销一次电汇。你无法取消一次 ACH 支付。现实世界是追加只读的，你的账本也应该如此。

```
❌ UPDATE ledger SET amount = 100 WHERE id = 1;  -- What was it before?
✅ INSERT INTO ledger (...) VALUES (...);         -- We reversed entry #1 for reason X
```

每一次修改都是一个新的条目。历史被保留。审计人员会很高兴。

### 为什么存在两个资金注入机制

**预留机制：** “我们是否有足够的资金来支付这些款项？”
**支付机制：** “在我们发送款项之前，我们是否仍然有足够的资金？”

预留和支付之间的时间可能长达数小时或数天。余额可能会发生变化。其他批次可能会运行。支付机制是最终的检查点，即使有人试图绕过它，它也会运行。

```python
# Commit time (Monday)
psp.commit_payroll_batch(batch)  # Reservation created

# Pay time (Wednesday)
psp.execute_payments(batch)      # Pay gate checks AGAIN before sending
```

### 为什么结算 ≠ 支付

“已发送支付”并不意味着“资金已转移”。ACH 支付需要 1-3 天。FedNow 支付是即时的，但仍然可能失败。电汇是同日结算，但费用较高。

PSP 跟踪整个生命周期：
```
Created → Submitted → Accepted → Settled (or Returned)
```

只有看到 `Settled`（已结算）状态，你才能获得确认。只有导入结算数据，你才能知道实际发生了什么。

### 为什么使用撤销而不是删除

当资金转移错误时，你需要一个撤销操作，即一个新的账本条目，用于抵消原始条目。这可以：

- 保留审计跟踪（原始条目 + 撤销条目）
- 显示 *何时* 进行了更正
- 记录 *原因*（退款代码，原因）

```sql
-- Original
INSERT INTO ledger (amount, ...) VALUES (1000, ...);

-- Reversal (not delete!)
INSERT INTO ledger (amount, reversed_entry_id, ...) VALUES (-1000, <original_id>, ...);
```

### 为什么幂等性是强制性的

网络故障会发生。重试是必要的。如果没有幂等性，就会导致重复支付。

PSP 中的每个操作都有一个幂等性密钥：
```python
result = psp.commit_payroll_batch(batch)
# First call: creates reservation, returns is_new=True
# Second call: finds existing, returns is_new=False, same reservation_id
```

调用者无需跟踪“我的调用是否成功？”——只需重试，直到获得结果。

## 这是什么

一个 **高质量的 PSP 核心**，适用于：

- 工资系统
- 零工经济平台
- 福利管理机构
- 财务管理
- 任何涉及资金流动的受监管的金融科技后端

## 这不是什么

这 **不是**：
- 一个 Stripe 的克隆（不包含商户注册和信用卡处理）
- 一个工资 SaaS（不包含税务计算和用户界面）
- 一个演示或原型（具有生产级别的约束）

请参阅 [docs/non_goals.md](docs/non_goals.md) 以获取明确的排除事项。

## 快速入门

```bash
# Start PostgreSQL
make up

# Apply migrations
make migrate

# Run the demo
make demo
```

演示展示了完整的生命周期：
1. 创建租户和账户
2. 充值账户
3. 提交工资批次（预留）
4. 执行支付
5. 模拟结算数据
6. 处理退款，并进行责任分类
7. 重新播放事件

## 库的使用

PSP 是一个库，而不是一个服务。请在您的应用程序中使用它。

```python
from payroll_engine.psp import PSP, PSPConfig, LedgerConfig, FundingGateConfig

# Explicit configuration (no magic, no env vars)
config = PSPConfig(
    tenant_id=tenant_id,
    legal_entity_id=legal_entity_id,
    ledger=LedgerConfig(require_balanced_entries=True),
    funding_gate=FundingGateConfig(pay_gate_enabled=True),  # NEVER False
    providers=[...],
    event_store=EventStoreConfig(),
)

# Single entry point
psp = PSP(session=session, config=config)

# Commit payroll (creates reservation)
commit_result = psp.commit_payroll_batch(batch)

# Execute payments (pay gate runs automatically)
execute_result = psp.execute_payments(batch)

# Ingest settlement feed
ingest_result = psp.ingest_settlement_feed(records)
```

## 文档

| 文档 | 目的 |
| ---------- | --------- |
| [docs/public_api.md](docs/public_api.md) | 公共 API 接口（稳定部分） |
| [docs/compat.md](docs/compat.md) | 版本控制和兼容性 |
| [docs/psp_invariants.md](docs/psp_invariants.md) | 系统不变性（保证部分） |
| [docs/idempotency.md](docs/idempotency.md) | 幂等性模式 |
| [docs/threat_model.md](docs/threat_model.md) | 安全分析 |
| [docs/non_goals.md](docs/non_goals.md) | PSP 不做的事情 |
| [docs/upgrading.md](docs/upgrading.md) | 升级和迁移指南 |
| [docs/runbooks/](docs/runbooks/) | 操作流程 |
| [docs/recipes/](docs/recipes/) | 集成示例 |

## API 稳定性承诺

**稳定（不会在不进行重大版本更新的情况下发生变化）：**
- `payroll_engine.psp` - PSP 接口和配置
- `payroll_engine.psp.providers` - 提供者协议
- `payroll_engine.psp.events` - 领域事件
- `payroll_engine.psp.ai` - AI 建议（配置和公共类型）

**内部（可能在未发出通知的情况下发生变化）：**
- `payroll_engine.psp.services.*` - 实现细节
- `payroll_engine.psp.ai.models.*` - 模型内部
- 任何以 `_` 开头的项

**AI 建议的限制（强制执行）：**
- 不能转移资金
- 不能写入账本条目
- 不能覆盖资金限制
- 不能做出结算决策
- 仅发出建议事件

请参阅 [docs/public_api.md](docs/public_api.md) 以获取完整的接口说明。

## 关键保证

| 保证 | 执行 |
| ----------- | ------------- |
| 资金始终为正数 | `CHECK (amount > 0)` |
| 不允许自转账 | `CHECK (debit != credit)` |
| 账本只能追加 | 不允许对条目进行 UPDATE/DELETE 操作 |
| 状态只能向前推进 | 触发器验证状态转换 |
| 事件是不可变的 | CI 中的模式版本控制 |
| 支付网关不能被绕过 | 在接口层强制执行 |
| AI 不能转移资金 | 架构约束 |

## 命令行工具

```bash
# Check database health
psp health

# Verify schema constraints
psp schema-check --database-url $DATABASE_URL

# Replay events
psp replay-events --tenant-id $TENANT --since "2025-01-01"

# Export events for audit
psp export-events --tenant-id $TENANT --output events.jsonl

# Query balance
psp balance --tenant-id $TENANT --account-id $ACCOUNT
```

## 安装

```bash
# Core only (ledger, funding gate, payments - that's it)
pip install payroll-engine

# With PostgreSQL driver
pip install payroll-engine[postgres]

# With async support
pip install payroll-engine[asyncpg]

# With AI advisory features (optional, disabled by default)
pip install payroll-engine[ai]

# Development
pip install payroll-engine[dev]

# Everything
pip install payroll-engine[all]
```

## 可选依赖项

PSP 的设计非常注重可选性。**核心资金转移功能不需要任何可选依赖项。**

| Extra | 它增加的内容 | 默认状态 |
| ------- | -------------- | --------------- |
| `[ai]` | 基于机器学习的 AI 模型（未来） | 规则基础不需要 |
| `[crypto]` | 区块链集成（未来） | **OFF** - reserved for future |
| `[postgres]` | PostgreSQL 驱动程序 | 只有在使用时才加载 |
| `[asyncpg]` | 异步 PostgreSQL | 只有在使用时才加载 |

### AI 建议：两层系统

**基于规则的 AI 不需要任何额外的组件。** 您可以获得：
- 风险评分
- 风险分析
- 操作手册辅助
- 假设模拟
- 租户风险分析

所有这些都只需要标准库。

```python
from payroll_engine.psp.ai import AdvisoryConfig, ReturnAdvisor

# Rules-baseline needs NO extras - just enable it
config = AdvisoryConfig(enabled=True, model_name="rules_baseline")
```

**机器学习模型（未来）需要 `[ai]` 扩展：**

```python
# Only needed for ML models, not rules-baseline
pip install payroll-engine[ai]

# Then use ML models
config = AdvisoryConfig(enabled=True, model_name="gradient_boost")
```

### AI 建议的限制（强制执行）

所有 AI 功能**永远不能**：
- 转移资金
- 写入账本条目
- 覆盖资金限制
- 做出结算决策

AI 仅发出建议事件，供人工或策略审查。

请参阅 [docs/public_api.md](docs/public_api.md) 以获取完整的可选性表。

## 测试

```bash
# Unit tests
make test

# With database
make test-psp

# Red team tests (constraint verification)
pytest tests/psp/test_red_team_scenarios.py -v
```

## 谁应该使用它

**如果您需要使用 PSP，请考虑以下情况：**
- 在受监管的环境中进行资金转移。
- 需要满足合规要求的审计跟踪。
- 更加注重准确性而非便捷性。
- 曾经在凌晨 3 点处理过支付失败问题。

**如果您不应该使用 PSP，请考虑以下情况：**
- 想要一个可以直接替代 Stripe 的解决方案。
- 需要一个完整的薪资管理系统。
- 倾向于遵循默认设置，而不是进行自定义配置。

## 贡献

请参考 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献指南。

主要规则：
- 任何新的公开 API 都必须更新 `docs/public_api.md` 文件。
- 事件模式的更改必须通过兼容性检查。
- 所有涉及资金的操作都需要使用幂等性密钥。

## 许可证

MIT 许可证。请参考 [LICENSE](LICENSE)。

---

*由那些因为支付失败而需要在凌晨 3 点被紧急召集的工程师开发。*
