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

**Un cœur de système de paiement (PSP) de qualité professionnelle, conçu autour d'une bibliothèque, pour la gestion de la paie et des transferts de fonds réglementés.**

Registre immuable en append-only. Contrôles explicites de financement. Événements reproductibles. Intelligence artificielle uniquement consultative (désactivée par défaut). Priorité à la correction plutôt qu'à la commodité.

## Points d'ancrage de confiance

Avant d'adopter cette bibliothèque, veuillez consulter :

| Documentation | Objectif |
| ---------- | --------- |
| [docs/psp_invariants.md](docs/psp_invariants.md) | Invariants du système (ce qui est garanti) |
| [docs/threat_model.md](docs/threat_model.md) | Analyse de sécurité |
| [docs/public_api.md](docs/public_api.md) | Contrat de l'API publique |
| [docs/compat.md](docs/compat.md) | Garanties de compatibilité |
| [docs/adoption_kit.md](docs/adoption_kit.md) | Guide d'évaluation et d'intégration |

*Nous savons que ce système gère des transactions financières. Ces documents prouvent que nous avons pris cela très au sérieux.*

---

## Pourquoi ce projet existe

La plupart des systèmes de paie traitent les transferts de fonds comme une fonctionnalité secondaire. Ils appellent une API de paiement, espèrent le meilleur et gèrent les échecs de manière réactive. Cela crée :

- **Échecs silencieux** : Les paiements disparaissent sans laisser de trace.
- **Cauchemars de rapprochement** : Les relevés bancaires ne correspondent pas aux enregistrements.
- **Confusion concernant les responsabilités** : En cas de remboursements, qui paie ?
- **Lacunes dans les audits** : Personne ne peut retracer ce qui s'est réellement passé.

Ce projet résout ces problèmes en traitant les transferts de fonds comme une priorité, avec une ingénierie financière appropriée.

## Principes fondamentaux

### Pourquoi les registres en append-only sont importants

Vous ne pouvez pas annuler un virement bancaire. Vous ne pouvez pas revenir sur l'envoi d'un paiement ACH. Le monde réel est basé sur l'append-only, et votre registre devrait l'être aussi.

```
❌ UPDATE ledger SET amount = 100 WHERE id = 1;  -- What was it before?
✅ INSERT INTO ledger (...) VALUES (...);         -- We reversed entry #1 for reason X
```

Chaque modification est une nouvelle entrée. L'historique est préservé. Les auditeurs sont satisfaits.

### Pourquoi deux contrôles de financement existent

**Contrôle de validation (Commit Gate)** : "Avons-nous suffisamment de fonds pour honorer ces paiements ?"
**Contrôle de paiement (Pay Gate)** : "Avons-nous toujours suffisamment de fonds juste avant d'envoyer les paiements ?"

Le temps entre la validation et le paiement peut être de quelques heures ou de quelques jours. Les soldes peuvent changer. D'autres traitements peuvent être lancés. Le contrôle de paiement est le dernier point de contrôle, et il est exécuté même si quelqu'un tente de le contourner.

```python
# Commit time (Monday)
psp.commit_payroll_batch(batch)  # Reservation created

# Pay time (Wednesday)
psp.execute_payments(batch)      # Pay gate checks AGAIN before sending
```

### Pourquoi le règlement ≠ le paiement

"Paiement envoyé" ne signifie pas "argent transféré". Les paiements ACH prennent 1 à 3 jours. FedNow est instantané, mais peut toujours échouer. Les virements bancaires sont effectués le jour même, mais sont coûteux.

PSP suit l'ensemble du cycle de vie :
```
Created → Submitted → Accepted → Settled (or Returned)
```

Vous n'avez pas de confirmation tant que vous ne voyez pas l'état `Confirmé`. Vous ne savez pas ce qui s'est réellement passé tant que vous n'avez pas intégré les données de règlement.

### Pourquoi les annulations existent au lieu des suppressions

Lorsqu'un paiement est effectué incorrectement, vous avez besoin d'une annulation, c'est-à-dire d'une nouvelle entrée dans le registre qui compense l'entrée originale. Cela permet de :

- Préserver la trace d'audit (entrée originale + annulation)
- Indiquer *quand* la correction a été effectuée
- Documenter *pourquoi* (code de retour, raison)

```sql
-- Original
INSERT INTO ledger (amount, ...) VALUES (1000, ...);

-- Reversal (not delete!)
INSERT INTO ledger (amount, reversed_entry_id, ...) VALUES (-1000, <original_id>, ...);
```

### Pourquoi l'idempotence est obligatoire

Des pannes réseau peuvent se produire. Les tentatives de relance sont nécessaires. Sans idempotence, vous risquez d'avoir des paiements en double.

Chaque opération dans PSP possède une clé d'idempotence :
```python
result = psp.commit_payroll_batch(batch)
# First call: creates reservation, returns is_new=True
# Second call: finds existing, returns is_new=False, same reservation_id
```

L'appelant n'a pas besoin de vérifier "mon appel a-t-il réussi ?" ; il suffit de réessayer jusqu'à obtenir un résultat.

## Ce qu'est ce projet

Un **cœur de système de paiement (PSP) de qualité professionnelle** adapté à :

- Les moteurs de paie
- Les plateformes de l'économie des petits boulots
- Les administrateurs de prestations
- La gestion de trésorerie
- Tout backend fintech réglementé qui effectue des transferts de fonds

## Ce que ce projet N'EST PAS

Ce n'est **pas** :
- Un clone de Stripe (pas d'intégration de commerçants, pas de traitement de cartes)
- Un logiciel SaaS de paie (pas de calcul de taxes, pas d'interface utilisateur)
- Une démonstration ou un prototype (contraintes de qualité production)

Consultez [docs/non_goals.md](docs/non_goals.md) pour connaître les objectifs non inclus.

## Démarrage rapide

```bash
# Start PostgreSQL
make up

# Apply migrations
make migrate

# Run the demo
make demo
```

La démonstration illustre l'ensemble du cycle de vie :
1. Création des locataires et des comptes
2. Alimentation du compte
3. Envoi d'un lot de paie (réservation)
4. Exécution des paiements
5. Simulation de la transmission des règlements
6. Gestion des retours avec classification des responsabilités
7. Relecture des événements

## Utilisation de la bibliothèque

PSP est une bibliothèque, pas un service. Utilisez-la dans votre application :

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

## Documentation

| Documentation | Objectif |
| ---------- | --------- |
| [docs/public_api.md](docs/public_api.md) | Contrat de l'API publique (ce qui est stable) |
| [docs/compat.md](docs/compat.md) | Gestion des versions et compatibilité |
| [docs/psp_invariants.md](docs/psp_invariants.md) | Invariants du système (ce qui est garanti) |
| [docs/idempotency.md](docs/idempotency.md) | Modèles d'idempotence |
| [docs/threat_model.md](docs/threat_model.md) | Analyse de sécurité |
| [docs/non_goals.md](docs/non_goals.md) | Ce que PSP ne fait pas |
| [docs/upgrading.md](docs/upgrading.md) | Guide de mise à niveau et de migration |
| [docs/runbooks/](docs/runbooks/) | Procédures opérationnelles |
| [docs/recipes/](docs/recipes/) | Exemples d'intégration |

## Promesse de stabilité de l'API

**Stable (ne se brisera pas sans une version majeure) :**
- `payroll_engine.psp` - Facade et configuration de PSP
- `payroll_engine.psp.providers` - Protocole des fournisseurs
- `payroll_engine.psp.events` - Événements du domaine
- `payroll_engine.psp.ai` - Conseils de l'IA (configuration et types publics)

**Interne (peut changer sans préavis) :**
- `payroll_engine.psp.services.*` - Détails de l'implémentation
- `payroll_engine.psp.ai.models.*` - Internes des modèles
- Tout ce qui commence par `_`

**Contraintes des conseils de l'IA (appliquées) :**
- Ne peut pas déplacer d'argent
- Ne peut pas écrire d'entrées de grand livre
- Ne peut pas outrepasser les mécanismes de financement
- Ne peut pas prendre de décisions de règlement
- Émet uniquement des événements de conseil

Consultez [docs/public_api.md](docs/public_api.md) pour le contrat complet.

## Garanties clés

| Garantie | Application |
| ----------- | ------------- |
| L'argent est toujours positif | `CHECK (amount > 0)` |
| Pas de transferts internes | `CHECK (debit != credit)` |
| Le grand livre est en append-only (uniquement en écriture) | Pas de modifications (UPDATE/DELETE) sur les entrées |
| L'état ne peut que progresser | Le déclencheur valide les transitions |
| Les événements sont immuables | Gestion des versions du schéma dans l'intégration continue (CI) |
| La passerelle de paiement ne peut pas être contournée | Appliqué dans la façade |
| L'IA ne peut pas déplacer d'argent | Contrainte architecturale |

## Outils en ligne de commande (CLI)

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

## Installation

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

## Dépendances optionnelles

PSP est conçu avec une optionnalité stricte. **Le transfert d'argent nécessite zéro dépendance optionnelle.**

| Extra | Ce que cela ajoute | État par défaut |
| ------- | -------------- | --------------- |
| `[ai]` | Modèles d'IA basés sur le machine learning (ML) (futur) | Non requis pour la base de règles |
| `[crypto]` | Intégrations blockchain (futur) | **OFF** - reserved for future |
| `[postgres]` | Pilote PostgreSQL | Ne se charge que si utilisé |
| `[asyncpg]` | PostgreSQL asynchrone | Ne se charge que si utilisé |

### Conseils de l'IA : Système à deux niveaux

**L'IA basée sur les règles fonctionne sans aucun élément supplémentaire.** Vous obtenez :
- Évaluation des risques
- Analyse des retours
- Assistance aux guides d'utilisation
- Simulation contrefactuelle
- Profilage des risques des locataires

Tout cela avec zéro dépendance au-delà de la bibliothèque standard.

```python
from payroll_engine.psp.ai import AdvisoryConfig, ReturnAdvisor

# Rules-baseline needs NO extras - just enable it
config = AdvisoryConfig(enabled=True, model_name="rules_baseline")
```

**Les modèles ML (futur) nécessitent les éléments supplémentaires `[ai]` :**

```python
# Only needed for ML models, not rules-baseline
pip install payroll-engine[ai]

# Then use ML models
config = AdvisoryConfig(enabled=True, model_name="gradient_boost")
```

### Contraintes des conseils de l'IA (appliquées)

Toutes les fonctionnalités de l'IA ne peuvent **jamais** :
- Déplacer de l'argent
- Écrire des entrées de grand livre
- Outrepasser les mécanismes de financement
- Prendre de décisions de règlement

L'IA émet uniquement des événements de conseil pour examen humain ou par les politiques.

Consultez [docs/public_api.md](docs/public_api.md) pour le tableau complet de l'optionnalité.

## Tests

```bash
# Unit tests
make test

# With database
make test-psp

# Red team tests (constraint verification)
pytest tests/psp/test_red_team_scenarios.py -v
```

## Qui devrait utiliser ceci

**Utilisez PSP si vous :**
- Effectuez des transactions financières dans des contextes réglementés.
- Avez besoin de pistes d'audit qui répondent aux exigences de conformité.
- Accordez plus d'importance à la justesse qu'à la simplicité.
- Avez déjà dû gérer des échecs de paiement à 3 heures du matin.

**N'utilisez pas PSP si vous :**
- Recherchez un remplacement direct de Stripe.
- Avez besoin d'une solution complète de gestion de la paie.
- Préférez les conventions aux configurations personnalisées.

## Contributions

Consultez le fichier [CONTRIBUTING.md](CONTRIBUTING.md) pour connaître les directives.

Règles importantes :
- Aucune nouvelle API publique sans mise à jour du fichier `docs/public_api.md`.
- Les modifications du schéma des événements doivent passer une vérification de compatibilité.
- Toutes les opérations financières nécessitent des clés d'idempotence.

## Licence

Licence MIT. Consultez le fichier [LICENSE](LICENSE).

---

*Développé par des ingénieurs qui ont été appelés en urgence à 3 heures du matin à cause d'échecs de paiement.*
