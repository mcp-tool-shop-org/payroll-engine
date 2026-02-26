<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  
            <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/payroll-engine/readme.png"
           alt="Payroll Engine logo" width="400">
</p>

<h1 align="center">Payroll Engine</h1>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/payroll-engine/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/payroll-engine/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/payroll-engine/"><img src="https://img.shields.io/pypi/v/payroll-engine" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/payroll-engine/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

**Um núcleo PSP de nível empresarial, focado em bibliotecas, para folha de pagamento e movimentação de dinheiro regulamentada.**

Livro-razão determinístico de apenas adição. Portas de financiamento explícitas. Eventos reproduzíveis. Inteligência artificial apenas consultiva (desativada por padrão). Correção em vez de conveniência.

## Pontos de Confiança

Antes de adotar esta biblioteca, revise:

| Documentação | Objetivo |
| ---------- | --------- |
| [docs/psp_invariants.md](docs/psp_invariants.md) | Invariantes do sistema (o que é garantido) |
| [docs/threat_model.md](docs/threat_model.md) | Análise de segurança |
| [docs/public_api.md](docs/public_api.md) | Contrato da API pública |
| [docs/compat.md](docs/compat.md) | Garantias de compatibilidade |
| [docs/adoption_kit.md](docs/adoption_kit.md) | Guia de avaliação e integração |

*Sabemos que isso envolve movimentação de dinheiro. Estes documentos comprovam que levamos isso a sério.*

---

## Por que isso existe

A maioria dos sistemas de folha de pagamento trata a movimentação de dinheiro como uma questão secundária. Eles chamam uma API de pagamento, esperam o melhor e lidam com falhas de forma reativa. Isso cria:

- **Falhas silenciosas**: Pagamentos desaparecem.
- **Pesadelos de conciliação**: Extratos bancários não correspondem aos registros.
- **Confusão de responsabilidade**: Quando ocorrem devoluções, quem paga?
- **Lacunas de auditoria**: Ninguém consegue rastrear o que realmente aconteceu.

Este projeto resolve esses problemas tratando a movimentação de dinheiro como uma prioridade, com a devida engenharia financeira.

## Princípios Fundamentais

### Por que os livros-razão de apenas adição são importantes

Você não pode desfazer uma transferência bancária. Você não pode cancelar um envio ACH. O mundo real é de apenas adição – portanto, seu livro-razão também deve ser.

```
❌ UPDATE ledger SET amount = 100 WHERE id = 1;  -- What was it before?
✅ INSERT INTO ledger (...) VALUES (...);         -- We reversed entry #1 for reason X
```

Cada modificação é uma nova entrada. O histórico é preservado. Os auditores ficam satisfeitos.

### Por que existem duas portas de financiamento

**Porta de Compromisso**: "Temos dinheiro suficiente para prometer esses pagamentos?"
**Porta de Pagamento**: "Ainda temos dinheiro antes de enviá-los?"

O tempo entre o compromisso e o pagamento pode ser de horas ou dias. Os saldos mudam. Outros lotes são executados. A porta de pagamento é o ponto de verificação final – ela é executada mesmo que alguém tente ignorá-la.

```python
# Commit time (Monday)
psp.commit_payroll_batch(batch)  # Reservation created

# Pay time (Wednesday)
psp.execute_payments(batch)      # Pay gate checks AGAIN before sending
```

### Por que Liquidação ≠ Pagamento

"Pagamento enviado" não é "dinheiro movido". Os pagamentos ACH levam de 1 a 3 dias. O FedNow é instantâneo, mas ainda pode falhar. A transferência bancária é no mesmo dia, mas é cara.

O PSP rastreia todo o ciclo de vida:
```
Created → Submitted → Accepted → Settled (or Returned)
```

Você só tem confirmação quando vê "Liquidado". Você só sabe o que realmente aconteceu quando ingere o feed de liquidação.

### Por que existem Reversões em vez de Exclusões

Quando o dinheiro é movido incorretamente, você precisa de uma reversão – uma nova entrada no livro-razão que compensa a original. Isso:

- Preserva o histórico de auditoria (original + reversão)
- Mostra *quando* a correção ocorreu
- Documenta *por que* (código de retorno, motivo)

```sql
-- Original
INSERT INTO ledger (amount, ...) VALUES (1000, ...);

-- Reversal (not delete!)
INSERT INTO ledger (amount, reversed_entry_id, ...) VALUES (-1000, <original_id>, ...);
```

### Por que a idempotência é obrigatória

Falhas de rede acontecem. As tentativas de repetição são necessárias. Sem idempotência, você obtém pagamentos duplicados.

Cada operação no PSP tem uma chave de idempotência:
```python
result = psp.commit_payroll_batch(batch)
# First call: creates reservation, returns is_new=True
# Second call: finds existing, returns is_new=False, same reservation_id
```

O chamador não precisa rastrear "minha chamada foi bem-sucedida?" – basta tentar novamente até obter um resultado.

## O que é isso

Um **núcleo PSP de nível empresarial** adequado para:

- Sistemas de folha de pagamento
- Plataformas da economia gig
- Administradores de benefícios
- Gestão de tesouraria
- Qualquer backend fintech regulamentado que mova dinheiro

## O que isso NÃO é

Isso **não é**:
- Um clone do Stripe (sem integração de comerciantes, sem processamento de cartões)
- Um SaaS de folha de pagamento (sem cálculo de impostos, sem interface do usuário)
- Uma demonstração ou protótipo (restrições de nível de produção)

Consulte [docs/non_goals.md](docs/non_goals.md) para os objetivos explícitos que não são alcançados.

## Início Rápido

```bash
# Start PostgreSQL
make up

# Apply migrations
make migrate

# Run the demo
make demo
```

A demonstração mostra o ciclo de vida completo:
1. Criar inquilinos e contas
2. Depositar fundos na conta
3. Executar um lote de folha de pagamento (reserva)
4. Executar pagamentos
5. Simular a conciliação
6. Lidar com uma devolução com classificação de responsabilidade
7. Reexecutar eventos

## Uso da Biblioteca

O PSP é uma biblioteca, não um serviço. Use-o dentro da sua aplicação:

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

## Documentação

| Documento | Propósito |
| ---------- | --------- |
| [docs/public_api.md](docs/public_api.md) | Contrato da API pública (o que é estável) |
| [docs/compat.md](docs/compat.md) | Versionamento e compatibilidade |
| [docs/psp_invariants.md](docs/psp_invariants.md) | Invariantes do sistema (o que é garantido) |
| [docs/idempotency.md](docs/idempotency.md) | Padrões de idempotência |
| [docs/threat_model.md](docs/threat_model.md) | Análise de segurança |
| [docs/non_goals.md](docs/non_goals.md) | O que o PSP não faz |
| [docs/upgrading.md](docs/upgrading.md) | Guia de atualização e migração |
| [docs/runbooks/](docs/runbooks/) | Procedimentos operacionais |
| [docs/recipes/](docs/recipes/) | Exemplos de integração |

## Promessa de Estabilidade da API

**Estável (não quebra sem uma nova versão principal):**
- `payroll_engine.psp` - Interface e configuração do PSP
- `payroll_engine.psp.providers` - Protocolo do provedor
- `payroll_engine.psp.events` - Eventos do domínio
- `payroll_engine.psp.ai` - Consultoria de IA (configuração e tipos públicos)

**Interno (pode mudar sem aviso prévio):**
- `payroll_engine.psp.services.*` - Detalhes da implementação
- `payroll_engine.psp.ai.models.*` - Detalhes dos modelos
- Qualquer coisa com o prefixo `_`

**Restrições da consultoria de IA (impostas):**
- Não pode mover dinheiro
- Não pode escrever entradas no livro-razão
- Não pode substituir as regras de financiamento
- Não pode tomar decisões de liquidação
- Emite apenas eventos de consultoria

Consulte [docs/public_api.md](docs/public_api.md) para o contrato completo.

## Garantias Principais

| Garantia | Imposição |
| ----------- | ------------- |
| O dinheiro é sempre positivo | `CHECK (amount > 0)` |
| Não há transferências para a mesma conta | `CHECK (debit != credit)` |
| O livro-razão é somente para anexar | Não há UPDATE/DELETE em entradas |
| O status só avança | O gatilho valida as transições |
| Os eventos são imutáveis | Versionamento do esquema no CI |
| O gateway de pagamento não pode ser ignorado | Imposto na interface |
| A IA não pode mover dinheiro | Restrição arquitetural |

## Ferramentas de Linha de Comando

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

## Instalação

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

## Dependências Opcionais

O PSP foi projetado com estrita opcionalidade. **O movimento central de dinheiro requer zero dependências opcionais.**

| Extra | O que ele adiciona | Estado Padrão |
| ------- | -------------- | --------------- |
| `[ai]` | Modelos de IA baseados em aprendizado de máquina (futuro) | Não são necessários para as regras básicas |
| `[crypto]` | Integrações com blockchain (futuro) | **OFF** - reserved for future |
| `[postgres]` | Driver do PostgreSQL | Não é carregado a menos que seja usado |
| `[asyncpg]` | PostgreSQL assíncrono | Não é carregado a menos que seja usado |

### Consultoria de IA: Sistema de Duas Camadas

**A IA básica baseada em regras funciona sem extras.** Você obtém:
- Avaliação de risco
- Análise de devoluções
- Assistência no livro de procedimentos
- Simulação contrafactual
- Perfil de risco do inquilino

Tudo com zero dependências além da biblioteca padrão.

```python
from payroll_engine.psp.ai import AdvisoryConfig, ReturnAdvisor

# Rules-baseline needs NO extras - just enable it
config = AdvisoryConfig(enabled=True, model_name="rules_baseline")
```

**Os modelos de IA (futuro) requerem os extras `[ai]:**

```python
# Only needed for ML models, not rules-baseline
pip install payroll-engine[ai]

# Then use ML models
config = AdvisoryConfig(enabled=True, model_name="gradient_boost")
```

### Restrições da Consultoria de IA (Impostas)

Todos os recursos de IA **nunca podem**:
- Mover dinheiro
- Escrever entradas no livro-razão
- Substituir as regras de financiamento
- Tomar decisões de liquidação

A IA emite apenas eventos de consultoria para revisão humana/política.

Consulte [docs/public_api.md](docs/public_api.md) para a tabela completa de opcionalidade.

## Testes

```bash
# Unit tests
make test

# With database
make test-psp

# Red team tests (constraint verification)
pytest tests/psp/test_red_team_scenarios.py -v
```

## Quem deve usar isso

**Use PSP se você:**
- Realiza transações financeiras em contextos regulamentados.
- Precisa de registros de auditoria que atendam aos requisitos de conformidade.
- Prioriza a correção em vez da conveniência.
- Já teve que lidar com falhas de pagamento às 3 da manhã.

**Não use PSP se você:**
- Procura uma alternativa direta ao Stripe.
- Precisa de uma solução completa de folha de pagamento.
- Prefere convenções a configurações personalizadas.

## Contribuições

Consulte o arquivo [CONTRIBUTING.md](CONTRIBUTING.md) para obter as diretrizes.

Regras importantes:
- Não é permitido criar novas APIs públicas sem atualizar o arquivo `docs/public_api.md`.
- As alterações no esquema de eventos devem passar em uma verificação de compatibilidade.
- Todas as operações financeiras exigem chaves de idempotência.

## Licença

Licença MIT. Consulte o arquivo [LICENSE](LICENSE).

---

*Desenvolvido por engenheiros que já foram chamados às 3 da manhã devido a falhas silenciosas em pagamentos.*
