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

**Un core PSP di livello libreria per la gestione delle buste paga e dei trasferimenti di denaro regolamentati.**

Registro immutabile con funzionalità di aggiunta. Meccanismi di autorizzazione espliciti. Eventi riproducibili. Intelligenza artificiale solo consultiva (disabilitata per impostazione predefinita). Correttezza al posto della comodità.

## Punti di riferimento di affidabilità

Prima di adottare questa libreria, consultare:

| Documentazione | Scopo |
| ---------- | --------- |
| [docs/psp_invariants.md](docs/psp_invariants.md) | Invarianti del sistema (ciò che è garantito) |
| [docs/threat_model.md](docs/threat_model.md) | Analisi della sicurezza |
| [docs/public_api.md](docs/public_api.md) | Contratto dell'API pubblica |
| [docs/compat.md](docs/compat.md) | Garanzie di compatibilità |
| [docs/adoption_kit.md](docs/adoption_kit.md) | Guida all'utilizzo e all'integrazione |

*Sappiamo che questo sistema gestisce denaro. Questi documenti dimostrano che lo abbiamo preso sul serio.*

---

## Perché questo progetto esiste

Nella maggior parte dei sistemi di gestione delle buste paga, i trasferimenti di denaro sono considerati un elemento secondario. Si richiama un'API di pagamento, si spera nel meglio e si affrontano i fallimenti in modo reattivo. Questo crea:

- **Errori silenziosi**: I pagamenti scompaiono nel nulla.
- **Incubi di riconciliazione**: Gli estratti conto bancari non corrispondono ai registri.
- **Confusione sulla responsabilità**: In caso di rimborsi, chi paga?
- **Lacune nella tracciabilità**: Nessuno può risalire a ciò che è realmente accaduto.

Questo progetto risolve questi problemi trattando i trasferimenti di denaro come un elemento fondamentale, con una corretta progettazione finanziaria.

## Principi fondamentali

### Perché i registri immutabili sono importanti

Non si può annullare un bonifico. Non si può "annullare" un pagamento ACH. Il mondo reale è immutabile: anche il vostro registro dovrebbe esserlo.

```
❌ UPDATE ledger SET amount = 100 WHERE id = 1;  -- What was it before?
✅ INSERT INTO ledger (...) VALUES (...);         -- We reversed entry #1 for reason X
```

Ogni modifica è una nuova voce. La cronologia viene preservata. I revisori sono soddisfatti.

### Perché esistono due meccanismi di autorizzazione

**Autorizzazione di impegno**: "Abbiamo i fondi necessari per effettuare questi pagamenti?"
**Autorizzazione di pagamento**: "Abbiamo ancora i fondi immediatamente prima di effettuare il pagamento?"

Il tempo tra l'impegno e il pagamento può variare da ore a giorni. I saldi possono cambiare. Altre operazioni possono essere eseguite. L'autorizzazione di pagamento è il controllo finale: viene eseguita anche se qualcuno tenta di aggirarla.

```python
# Commit time (Monday)
psp.commit_payroll_batch(batch)  # Reservation created

# Pay time (Wednesday)
psp.execute_payments(batch)      # Pay gate checks AGAIN before sending
```

### Perché la liquidazione non è uguale al pagamento

"Pagamento inviato" non significa "denaro trasferito". I pagamenti ACH richiedono da 1 a 3 giorni. FedNow è istantaneo, ma può comunque fallire. I bonifici sono eseguiti nello stesso giorno, ma sono costosi.

PSP tiene traccia dell'intero ciclo di vita:
```
Created → Submitted → Accepted → Settled (or Returned)
```

Non si ha conferma finché non si vede lo stato `Liquidato`. Non si sa cosa è realmente accaduto finché non si integra il flusso di liquidazione.

### Perché esistono le operazioni di annullamento invece delle cancellazioni

Quando un pagamento viene effettuato in modo errato, è necessario un annullamento: una nuova voce nel registro che compensa l'operazione originale. Questo:

- Preserva la traccia delle operazioni (operazione originale + annullamento).
- Mostra *quando* è stata effettuata la correzione.
- Documenta *perché* (codice di restituzione, motivo).

```sql
-- Original
INSERT INTO ledger (amount, ...) VALUES (1000, ...);

-- Reversal (not delete!)
INSERT INTO ledger (amount, reversed_entry_id, ...) VALUES (-1000, <original_id>, ...);
```

### Perché l'idempotenza è obbligatoria

Si verificano errori di rete. I tentativi di ripetizione sono necessari. Senza idempotenza, si verificano pagamenti doppi.

Ogni operazione in PSP ha una chiave di idempotenza:
```python
result = psp.commit_payroll_batch(batch)
# First call: creates reservation, returns is_new=True
# Second call: finds existing, returns is_new=False, same reservation_id
```

Il chiamante non deve tenere traccia di "la mia chiamata ha avuto successo?": basta tentare nuovamente finché non si ottiene un risultato.

## Cos'è questo

Un **core PSP di livello professionale** adatto per:

- Sistemi di gestione delle buste paga
- Piattaforme dell'economia collaborativa
- Amministratori di benefit
- Gestione della tesoreria
- Qualsiasi backend fintech regolamentato che gestisce denaro

## Cosa questo NON è

Questo **non è**:
- Un clone di Stripe (nessuna registrazione di commercianti, nessuna elaborazione di carte).
- Un servizio SaaS per la gestione delle buste paga (nessun calcolo delle tasse, nessuna interfaccia utente).
- Una demo o un prototipo (vincoli di livello di produzione).

Consultare [docs/non_goals.md](docs/non_goals.md) per un elenco esplicito di ciò che questo progetto non è.

## Guida all'avvio rapido

```bash
# Start PostgreSQL
make up

# Apply migrations
make migrate

# Run the demo
make demo
```

La demo mostra l'intero ciclo di vita:
1. Creazione di tenant e account
2. Ricarica dell'account
3. Esecuzione di un batch di pagamenti (prenotazione)
4. Esecuzione dei pagamenti
5. Simulazione del flusso di compensazione
6. Gestione di un rimborso con classificazione delle responsabilità
7. Riproduzione degli eventi

## Utilizzo della libreria

PSP è una libreria, non un servizio. Utilizzala all'interno della tua applicazione:

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

## Documentazione

| Documento | Scopo |
| ---------- | --------- |
| [docs/public_api.md](docs/public_api.md) | Contratto dell'API pubblica (ciò che è stabile) |
| [docs/compat.md](docs/compat.md) | Versionamento e compatibilità |
| [docs/psp_invariants.md](docs/psp_invariants.md) | Invarianti del sistema (ciò che è garantito) |
| [docs/idempotency.md](docs/idempotency.md) | Modelli di idempotenza |
| [docs/threat_model.md](docs/threat_model.md) | Analisi della sicurezza |
| [docs/non_goals.md](docs/non_goals.md) | Cosa PSP non fa |
| [docs/upgrading.md](docs/upgrading.md) | Guida all'aggiornamento e alla migrazione |
| [docs/runbooks/](docs/runbooks/) | Procedure operative |
| [docs/recipes/](docs/recipes/) | Esempi di integrazione |

## Promessa di stabilità dell'API

**Stabile (non si interrompe senza una nuova versione principale):**
- `payroll_engine.psp` - Facciata e configurazione di PSP
- `payroll_engine.psp.providers` - Protocollo dei provider
- `payroll_engine.psp.events` - Eventi del dominio
- `payroll_engine.psp.ai` - Consulenza AI (configurazione e tipi pubblici)

**Interno (può cambiare senza preavviso):**
- `payroll_engine.psp.services.*` - Dettagli dell'implementazione
- `payroll_engine.psp.ai.models.*` - Interni dei modelli
- Tutto ciò che ha un prefisso `_`

**Vincoli della consulenza AI (applicati):**
- Non è possibile spostare denaro
- Non è possibile scrivere voci nel registro
- Non è possibile ignorare i controlli di finanziamento
- Non è possibile prendere decisioni di compensazione
- Emette solo eventi di consulenza

Consulta [docs/public_api.md](docs/public_api.md) per il contratto completo.

## Garanzie principali

| Garanzia | Applicazione |
| ----------- | ------------- |
| Il denaro è sempre positivo | `CHECK (amount > 0)` |
| Nessun trasferimento a se stessi | `CHECK (debit != credit)` |
| Il registro è scrivibile solo in aggiunta | Nessuna operazione di UPDATE/DELETE sulle voci |
| Lo stato può solo avanzare | Il trigger convalida le transizioni |
| Gli eventi sono immutabili | Versionamento dello schema nell'integrazione continua |
| Il gateway di pagamento non può essere bypassato | Applicato nella facciata |
| L'AI non può spostare denaro | Vincolo architetturale |

## Strumenti CLI

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

## Installazione

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

## Dipendenze opzionali

PSP è progettata con una stretta opzionalità. **Il trasferimento di denaro richiede zero dipendenze opzionali.**

| Extra | Cosa aggiunge | Stato predefinito |
| ------- | -------------- | --------------- |
| `[ai]` | Modelli AI basati su machine learning (futuro) | Non necessari per le regole di base |
| `[crypto]` | Integrazioni blockchain (futuro) | **OFF** - reserved for future |
| `[postgres]` | Driver PostgreSQL | Caricato solo se utilizzato |
| `[asyncpg]` | PostgreSQL asincrono | Caricato solo se utilizzato |

### Consulenza AI: Sistema a due livelli

**L'AI basata su regole funziona senza alcun extra.** Si ottiene:
- Valutazione del rischio
- Analisi dei resi
- Assistenza alla documentazione operativa
- Simulazione controfattuale
- Profilazione del rischio del tenant

Tutto questo con zero dipendenze oltre alla libreria standard.

```python
from payroll_engine.psp.ai import AdvisoryConfig, ReturnAdvisor

# Rules-baseline needs NO extras - just enable it
config = AdvisoryConfig(enabled=True, model_name="rules_baseline")
```

**I modelli ML (futuro) richiedono gli extra `[ai]:**

```python
# Only needed for ML models, not rules-baseline
pip install payroll-engine[ai]

# Then use ML models
config = AdvisoryConfig(enabled=True, model_name="gradient_boost")
```

### Vincoli della consulenza AI (applicati)

Tutte le funzionalità AI **non possono mai**:
- Spostare denaro
- Scrivere voci nel registro
- Ignorare i controlli di finanziamento
- Prendere decisioni di compensazione

L'AI emette solo eventi di consulenza per la revisione umana/politica.

Consulta [docs/public_api.md](docs/public_api.md) per la tabella completa delle opzioni.

## Test

```bash
# Unit tests
make test

# With database
make test-psp

# Red team tests (constraint verification)
pytest tests/psp/test_red_team_scenarios.py -v
```

## Chi dovrebbe utilizzare questo

**Utilizzate PSP se:**
- Gestite transazioni finanziarie in contesti regolamentati.
- Avete bisogno di registrazioni dettagliate che soddisfino i requisiti di conformità.
- Date priorità alla correttezza rispetto alla comodità.
- Avete già dovuto gestire errori di pagamento alle 3 del mattino.

**Non utilizzate PSP se:**
- Cercate una soluzione alternativa a Stripe, facile da integrare.
- Avete bisogno di una soluzione completa per la gestione delle buste paga.
- Preferite soluzioni standardizzate piuttosto che configurazioni personalizzate.

## Contributi

Consultate il file [CONTRIBUTING.md](CONTRIBUTING.md) per le linee guida.

Regole principali:
- Non è possibile aggiungere nuove API pubbliche senza aggiornare il file `docs/public_api.md`.
- Le modifiche allo schema degli eventi devono superare un controllo di compatibilità.
- Tutte le operazioni che coinvolgono denaro richiedono chiavi di idempotenza.

## Licenza

Licenza MIT. Consultate il file [LICENSE](LICENSE).

---

*Sviluppato da ingegneri che sono stati chiamati urgentemente alle 3 del mattino a causa di errori silenziosi nei pagamenti.*
