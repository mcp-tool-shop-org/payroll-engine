<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/payroll-engine/main/logo.png" alt="Payroll Engine logo" width="400">
</p>

<h1 align="center">Payroll Engine</h1>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/payroll-engine/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/payroll-engine/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/payroll-engine/"><img src="https://img.shields.io/pypi/v/payroll-engine" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/payroll-engine/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

**給与計算および規制対象の資金移動のための、ライブラリを重視したPSPコア。**

変更不可能な追加専用の台帳。明示的な資金調達ゲート。再現可能なイベント。アドバイスのみのAI（デフォルトでは無効）。正確性を優先し、利便性を後回しにする。

## 信頼の基盤

このライブラリを使用する前に、以下の内容を確認してください。

| ドキュメント | 目的 |
| ---------- | --------- |
| [docs/psp_invariants.md](docs/psp_invariants.md) | システムの不変条件（保証されること） |
| [docs/threat_model.md](docs/threat_model.md) | セキュリティ分析 |
| [docs/public_api.md](docs/public_api.md) | 公開APIの契約 |
| [docs/compat.md](docs/compat.md) | 互換性の保証 |
| [docs/adoption_kit.md](docs/adoption_kit.md) | 評価と組み込みガイド |

*私たちは、このシステムが資金を移動することを理解しています。これらのドキュメントは、私たちがそれを真剣に受け止めていることを証明しています。*

---

## このシステムが存在する理由

ほとんどの給与システムでは、資金移動は後回しにされることが多いです。支払いAPIを呼び出し、最善を祈り、問題が発生した場合は、その都度対応します。これにより、以下のような問題が発生します。

- **サイレントエラー**: 支払いが闇に消える
- **照合の悪夢**: 銀行の明細と記録が一致しない
- **責任の混乱**: 払い戻しが発生した場合、誰が支払うのか？
- **監査の欠落**: 何が実際に起こったのかを追跡できない

このプロジェクトは、適切な財務工学を用いて、資金移動を最優先事項として扱うことで、これらの問題を解決します。

## 主要な原則

### 追加専用の台帳が重要な理由

銀行振込を元に戻すことはできません。ACHの送信を取り消すこともできません。現実世界は追加専用です。そのため、台帳も同様であるべきです。

```
❌ UPDATE ledger SET amount = 100 WHERE id = 1;  -- What was it before?
✅ INSERT INTO ledger (...) VALUES (...);         -- We reversed entry #1 for reason X
```

すべての変更は新しいエントリとして記録されます。履歴は保持されます。監査担当者は満足します。

### 2つの資金調達ゲートが存在する理由

**コミットゲート**: 「これらの支払いを約束するために、十分な資金がありますか？」
**ペイゲート**: 「実際に送金する直前に、まだ十分な資金がありますか？」

コミットとペイの間の時間は、数時間から数日になる可能性があります。残高は変化します。他の処理も実行されます。ペイゲートは最終的なチェックポイントであり、誰かがそれを回避しようとしても、実行されます。

```python
# Commit time (Monday)
psp.commit_payroll_batch(batch)  # Reservation created

# Pay time (Wednesday)
psp.execute_payments(batch)      # Pay gate checks AGAIN before sending
```

### 決済 ≠ 支払い

「支払いが送信されました」は「資金が移動されました」を意味しません。ACHには1〜3日かかります。FedNowは即時ですが、それでも失敗する可能性があります。銀行振込は当日ですが、高額です。

PSPは、資金のライフサイクル全体を追跡します。
```
Created → Submitted → Accepted → Settled (or Returned)
```

`Settled`と表示されるまで、確認はありません。決済情報を取り込むまで、実際に何が起こったのかはわかりません。

### 削除ではなく、リバースが存在する理由

資金が誤って移動した場合、元のエントリを相殺する新しい台帳エントリである、リバースが必要です。これにより、以下のことが可能になります。

- 監査証跡を保持します（元のエントリ + リバース）
- 修正が行われたタイミングを示します
- 理由を文書化します（リターンコード、理由）

```sql
-- Original
INSERT INTO ledger (amount, ...) VALUES (1000, ...);

-- Reversal (not delete!)
INSERT INTO ledger (amount, reversed_entry_id, ...) VALUES (-1000, <original_id>, ...);
```

### 멱等性（べき等性）が必須である理由

ネットワーク障害が発生する可能性があります。再試行は必要です。멱等性がないと、二重支払いが発生します。

PSPのすべての操作には、멱等性キーがあります。
```python
result = psp.commit_payroll_batch(batch)
# First call: creates reservation, returns is_new=True
# Second call: finds existing, returns is_new=False, same reservation_id
```

呼び出し側は、「自分の呼び出しは成功しましたか？」を追跡する必要はありません。結果が得られるまで、単に再試行するだけです。

## これは何ですか？

**リファレンスグレードのPSPコア**で、以下の用途に適しています。

- 給与計算エンジン
- ギグエコノミープラットフォーム
- 福利管理者
- 財務管理
- 資金を移動するすべての規制対象の金融テクノロジーのバックエンド

## これは何ではありませんか？

これは**以下ではありません**:
- Stripeのクローン（加盟店登録、カード処理なし）
- 給与SaaS（税金計算、UIなし）
- デモまたはプロトタイプ（本番環境での制約）

明示的な非目標については、[docs/non_goals.md](docs/non_goals.md)を参照してください。

## クイックスタート

```bash
# Start PostgreSQL
make up

# Apply migrations
make migrate

# Run the demo
make demo
```

デモでは、以下の全ライフサイクルが示されています。
1. テナントとアカウントの作成
2. アカウントへの入金
3. 給与バッチ（予約）の実行
4. 支払い処理
5. 決済データのシミュレーション
6. 責任分類付きの返金処理
7. イベントの再実行

## ライブラリの使用

PSPはサービスではなく、ライブラリです。アプリケーション内でご使用ください。

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

## ドキュメント

| ドキュメント | 目的 |
| ---------- | --------- |
| [docs/public_api.md](docs/public_api.md) | 公開APIの仕様（安定版） |
| [docs/compat.md](docs/compat.md) | バージョン管理と互換性 |
| [docs/psp_invariants.md](docs/psp_invariants.md) | システムの制約（保証事項） |
| [docs/idempotency.md](docs/idempotency.md) | 冪等性パターン |
| [docs/threat_model.md](docs/threat_model.md) | セキュリティ分析 |
| [docs/non_goals.md](docs/non_goals.md) | PSPが行わないこと |
| [docs/upgrading.md](docs/upgrading.md) | アップグレードと移行ガイド |
| [docs/runbooks/](docs/runbooks/) | 運用手順 |
| [docs/recipes/](docs/recipes/) | 統合の例 |

## APIの安定性に関する約束

**安定版（メジャーバージョン変更なしで動作）:**
- `payroll_engine.psp` - PSPのファサードと設定
- `payroll_engine.psp.providers` - プロバイダープロトコル
- `payroll_engine.psp.events` - ドメインイベント
- `payroll_engine.psp.ai` - AIアドバイザリ（設定と公開型）

**内部版（予告なく変更される可能性あり）:**
- `payroll_engine.psp.services.*` - 実装の詳細
- `payroll_engine.psp.ai.models.*` - モデルの内部構造
- `_`で始まるもの

**AIアドバイザリの制約（強制）:**
- 資金の移動は不可
- 勘定科目の書き込みは不可
- 資金調達の制限のオーバーライドは不可
- 決済の決定は不可
- アドバイザリイベントのみを発行

完全な仕様については、[docs/public_api.md](docs/public_api.md) を参照してください。

## 重要な保証事項

| 保証 | 適用 |
| ----------- | ------------- |
| 金額は常に正の値 | `CHECK (amount > 0)` |
| 自己送金は不可 | `CHECK (debit != credit)` |
| 勘定科目は追記のみ | エントリのUPDATE/DELETEは不可 |
| ステータスは常に進行方向にのみ変化 | トリガーは遷移を検証 |
| イベントは不変 | CIにおけるスキーマのバージョン管理 |
| 決済ゲートを回避することは不可 | ファサードで適用 |
| AIは資金を移動できない | アーキテクチャ上の制約 |

## CLIツール

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

## インストール

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

## オプションの依存関係

PSPは、厳格なオプション機能を採用しています。**コアとなる資金移動には、オプションの依存関係は一切不要です。**

| Extra | 追加機能 | デフォルトの状態 |
| ------- | -------------- | --------------- |
| `[ai]` | 機械学習ベースのAIモデル（将来） | ルールベースの機能には不要 |
| `[crypto]` | ブロックチェーン連携（将来） | **OFF** - reserved for future |
| `[postgres]` | PostgreSQLドライバ | 使用しない場合はロードされません |
| `[asyncpg]` | 非同期PostgreSQL | 使用しない場合はロードされません |

### AIアドバイザリ：二層システム

**ルールベースのAIは、追加機能なしで動作します。** 以下の機能が利用可能です。
- リスクスコアリング
- リターン分析
- 運用マニュアルのサポート
- シミュレーション
- テナントのリスクプロファイリング

これらは、標準ライブラリ以外の依存関係を一切必要としません。

```python
from payroll_engine.psp.ai import AdvisoryConfig, ReturnAdvisor

# Rules-baseline needs NO extras - just enable it
config = AdvisoryConfig(enabled=True, model_name="rules_baseline")
```

**機械学習モデル（将来）には、`[ai]`の追加機能が必要です。**

```python
# Only needed for ML models, not rules-baseline
pip install payroll-engine[ai]

# Then use ML models
config = AdvisoryConfig(enabled=True, model_name="gradient_boost")
```

### AIアドバイザリの制約（強制）

すべてのAI機能は、以下のことは**一切できません**。
- 資金の移動
- 勘定科目の書き込み
- 資金調達の制限のオーバーライド
- 決済の決定

AIは、アドバイザリイベントのみを発行し、人間のレビューやポリシーの確認のために使用されます。

オプション機能の詳細については、[docs/public_api.md](docs/public_api.md) を参照してください。

## テスト

```bash
# Unit tests
make test

# With database
make test-psp

# Red team tests (constraint verification)
pytest tests/psp/test_red_team_scenarios.py -v
```

## このツールを使用すべきユーザー

**PSP（Payment Service Provider）をご利用になる場合：**
- 規制された環境で資金移動を行う場合
- コンプライアンス要件を満たす監査ログが必要な場合
- 利便性よりも正確性を重視する場合
- 深夜3時に支払いエラーが発生した対応経験がある場合

**PSPをご利用にならない場合：**
- Stripeの代替となる簡単なソリューションを求めている場合
- 完全な給与計算システムが必要な場合
- 設定よりも標準的な方法を好む場合

## 貢献について

詳細については、[CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

主なルール：
- `docs/public_api.md` を更新せずに、新しい公開APIを追加することはできません。
- イベントスキーマの変更は、互換性チェックに合格する必要があります。
- すべての資金関連の操作には、冪等性キーが必要です。

## ライセンス

MITライセンス。詳細については、[LICENSE](LICENSE) を参照してください。

---

*深夜3時に支払いエラーで緊急対応を求められたエンジニアによって開発されました。*
