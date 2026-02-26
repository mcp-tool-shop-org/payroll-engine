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

**Un núcleo PSP de grado profesional, diseñado para la gestión de nóminas y transferencias de dinero reguladas.**

Un registro inmutable de tipo "append-only". Mecanismos de autorización explícitos. Eventos reproducibles. Inteligencia artificial solo con fines de asesoramiento (desactivada por defecto). Prioridad a la corrección sobre la conveniencia.

## Puntos de Confianza

Antes de adoptar esta biblioteca, revise:

| Documentación | Propósito |
| ---------- | --------- |
| [docs/psp_invariants.md](docs/psp_invariants.md) | Invariantes del sistema (lo que está garantizado) |
| [docs/threat_model.md](docs/threat_model.md) | Análisis de seguridad |
| [docs/public_api.md](docs/public_api.md) | Contrato de la API pública |
| [docs/compat.md](docs/compat.md) | Garantías de compatibilidad |
| [docs/adoption_kit.md](docs/adoption_kit.md) | Guía de evaluación e integración |

*Sabemos que esto implica el movimiento de dinero. Estos documentos demuestran que lo hemos tomado en serio.*

---

## ¿Por qué existe esto?

La mayoría de los sistemas de nóminas tratan el movimiento de dinero como una cuestión secundaria. Llaman a una API de pago, esperan lo mejor y reaccionan ante los fallos. Esto crea:

- **Fallos silenciosos**: Los pagos desaparecen sin dejar rastro.
- **Pesadillas de conciliación**: Los extractos bancarios no coinciden con los registros.
- **Confusión en la responsabilidad**: Cuando hay devoluciones, ¿quién paga?
- **Lagunas en la auditoría**: Nadie puede rastrear lo que realmente sucedió.

Este proyecto resuelve estos problemas al tratar el movimiento de dinero como una preocupación fundamental, utilizando una ingeniería financiera adecuada.

## Principios Fundamentales

### ¿Por qué son importantes los registros de tipo "append-only"?

No se puede deshacer una transferencia bancaria. No se puede cancelar un envío ACH. El mundo real es de tipo "append-only", por lo que su registro también debería serlo.

```
❌ UPDATE ledger SET amount = 100 WHERE id = 1;  -- What was it before?
✅ INSERT INTO ledger (...) VALUES (...);         -- We reversed entry #1 for reason X
```

Cada modificación es una nueva entrada. La historia se conserva. Los auditores estarán contentos.

### ¿Por qué existen dos mecanismos de autorización?

**Mecanismo de Compromiso ("Commit Gate"):** "¿Tenemos el dinero para cumplir con estos pagos?"
**Mecanismo de Pago ("Pay Gate"):** "¿Todavía tenemos el dinero justo antes de enviarlos?"

El tiempo entre el compromiso y el pago puede ser de horas o días. Los saldos cambian. Se ejecutan otros procesos. El mecanismo de pago es el último control; se ejecuta incluso si alguien intenta eludirlo.

```python
# Commit time (Monday)
psp.commit_payroll_batch(batch)  # Reservation created

# Pay time (Wednesday)
psp.execute_payments(batch)      # Pay gate checks AGAIN before sending
```

### ¿Por qué el "asentamiento" no es lo mismo que el "pago"?

"Pago enviado" no es lo mismo que "dinero movido". Los envíos ACH tardan de 1 a 3 días. FedNow es instantáneo, pero aún puede fallar. Las transferencias bancarias son el mismo día, pero son costosas.

PSP rastrea todo el ciclo de vida:
```
Created → Submitted → Accepted → Settled (or Returned)
```

No tendrá confirmación hasta que vea "Asentado". No sabrá lo que realmente sucedió hasta que importe el flujo de datos de liquidación.

### ¿Por qué existen las anulaciones en lugar de las eliminaciones?

Cuando el dinero se mueve incorrectamente, necesita una anulación: una nueva entrada en el registro que compensa la entrada original. Esto:

- Conserva el rastro de auditoría (entrada original + anulación).
- Muestra *cuándo* se realizó la corrección.
- Documenta *por qué* (código de devolución, motivo).

```sql
-- Original
INSERT INTO ledger (amount, ...) VALUES (1000, ...);

-- Reversal (not delete!)
INSERT INTO ledger (amount, reversed_entry_id, ...) VALUES (-1000, <original_id>, ...);
```

### ¿Por qué la idempotencia es obligatoria?

Los fallos de red ocurren. Los reintentos son necesarios. Sin idempotencia, se producen pagos duplicados.

Cada operación en PSP tiene una clave de idempotencia:
```python
result = psp.commit_payroll_batch(batch)
# First call: creates reservation, returns is_new=True
# Second call: finds existing, returns is_new=False, same reservation_id
```

El llamador no necesita rastrear "¿tuvo éxito mi llamada?". Simplemente reintente hasta que obtenga un resultado.

## ¿Qué es esto?

Un **núcleo PSP de grado profesional** adecuado para:

- Sistemas de nóminas
- Plataformas de la economía colaborativa
- Administradores de beneficios
- Gestión de tesorería
- Cualquier backend fintech regulado que gestione transferencias de dinero.

## ¿Qué NO es esto?

Esto **no es**:
- Un clon de Stripe (sin incorporación de comerciantes, sin procesamiento de tarjetas).
- Un SaaS de nóminas (sin cálculo de impuestos, sin interfaz de usuario).
- Una demostración o prototipo (con restricciones de grado de producción).

Consulte [docs/non_goals.md](docs/non_goals.md) para ver los objetivos explícitos que no se cumplen.

## Comienzo rápido

```bash
# Start PostgreSQL
make up

# Apply migrations
make migrate

# Run the demo
make demo
```

La demostración muestra el ciclo de vida completo:
1. Crear inquilinos y cuentas.
2. Financiar la cuenta.
3. Ejecutar un lote de nómina (reserva).
4. Ejecutar pagos.
5. Simular la conciliación.
6. Gestionar una devolución con clasificación de responsabilidad.
7. Replicar eventos.

## Uso de la biblioteca

PSP es una biblioteca, no un servicio. Úsela dentro de su aplicación:

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

## Documentación

| Documento | Propósito |
| ---------- | --------- |
| [docs/public_api.md](docs/public_api.md) | Contrato de la API pública (lo que es estable) |
| [docs/compat.md](docs/compat.md) | Versionado y compatibilidad |
| [docs/psp_invariants.md](docs/psp_invariants.md) | Invariantes del sistema (lo que está garantizado) |
| [docs/idempotency.md](docs/idempotency.md) | Patrones de idempotencia |
| [docs/threat_model.md](docs/threat_model.md) | Análisis de seguridad |
| [docs/non_goals.md](docs/non_goals.md) | Lo que PSP no hace |
| [docs/upgrading.md](docs/upgrading.md) | Guía de actualización y migración |
| [docs/runbooks/](docs/runbooks/) | Procedimientos operativos |
| [docs/recipes/](docs/recipes/) | Ejemplos de integración |

## Promesa de estabilidad de la API

**Estable (no se romperá sin un cambio de versión importante):**
- `payroll_engine.psp` - Fachada y configuración de PSP.
- `payroll_engine.psp.providers` - Protocolo de proveedores.
- `payroll_engine.psp.events` - Eventos del dominio.
- `payroll_engine.psp.ai` - Asesoramiento de IA (configuración y tipos públicos).

**Interno (puede cambiar sin previo aviso):**
- `payroll_engine.psp.services.*` - Detalles de implementación.
- `payroll_engine.psp.ai.models.*` - Internos del modelo.
- Cualquier cosa con el prefijo `_`.

**Restricciones del asesoramiento de IA (aplicadas):**
- No se puede mover dinero.
- No se pueden escribir entradas en el libro mayor.
- No se pueden anular las restricciones de financiación.
- No se pueden tomar decisiones de conciliación.
- Solo emite eventos de asesoramiento.

Consulte [docs/public_api.md](docs/public_api.md) para ver el contrato completo.

## Garantías clave

| Garantía | Aplicación |
| ----------- | ------------- |
| El dinero siempre es positivo. | `CHECK (amount > 0)` |
| No hay transferencias internas. | `CHECK (debit != credit)` |
| El libro mayor solo se puede agregar. | No se pueden realizar operaciones de UPDATE/DELETE en las entradas. |
| El estado solo puede avanzar. | El disparador valida las transiciones. |
| Los eventos son inmutables. | Versionado del esquema en CI. |
| No se puede eludir la puerta de pago. | Aplicado en la fachada. |
| La IA no puede mover dinero. | Restricción arquitectónica. |

## Herramientas de línea de comandos (CLI)

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

## Instalación

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

## Dependencias opcionales

PSP está diseñado con una estricta opcionalidad. **El movimiento de dinero central requiere cero dependencias opcionales.**

| Extra | Lo que agrega | Estado predeterminado |
| ------- | -------------- | --------------- |
| `[ai]` | Modelos de IA basados en ML (futuro) | No es necesario para la línea de base de reglas. |
| `[crypto]` | Integraciones con blockchain (futuro) | **OFF** - reserved for future |
| `[postgres]` | Controlador de PostgreSQL | No se carga a menos que se utilice. |
| `[asyncpg]` | PostgreSQL asíncrono | No se carga a menos que se utilice. |

### Asesoramiento de IA: Sistema de dos niveles

**La IA de línea de base de reglas funciona sin ningún extra.** Obtiene:
- Puntuación de riesgos.
- Análisis de devoluciones.
- Asistencia para el libro de operaciones.
- Simulación contrafáctica.
- Perfil de riesgo del inquilino.

Todo con cero dependencias más allá de la biblioteca estándar.

```python
from payroll_engine.psp.ai import AdvisoryConfig, ReturnAdvisor

# Rules-baseline needs NO extras - just enable it
config = AdvisoryConfig(enabled=True, model_name="rules_baseline")
```

**Los modelos de ML (futuro) requieren los extras `[ai]:**

```python
# Only needed for ML models, not rules-baseline
pip install payroll-engine[ai]

# Then use ML models
config = AdvisoryConfig(enabled=True, model_name="gradient_boost")
```

### Restricciones del asesoramiento de IA (aplicadas)

Todas las funciones de IA **nunca** pueden:
- Mover dinero.
- Escribir entradas en el libro mayor.
- Anular las restricciones de financiación.
- Tomar decisiones de conciliación.

La IA solo emite eventos de asesoramiento para su revisión por humanos o políticas.

Consulte [docs/public_api.md](docs/public_api.md) para ver la tabla de opcionalidad completa.

## Pruebas

```bash
# Unit tests
make test

# With database
make test-psp

# Red team tests (constraint verification)
pytest tests/psp/test_red_team_scenarios.py -v
```

## ¿Quién debería usar esto?

**Utilice PSP si:**
- Realiza transacciones financieras en contextos regulados.
- Necesita registros de auditoría que cumplan con los requisitos de cumplimiento.
- Prioriza la precisión sobre la conveniencia.
- Ha tenido que solucionar problemas de fallos de pago a las 3 de la mañana.

**No utilice PSP si:**
- Busca un reemplazo directo de Stripe.
- Necesita una solución completa de nómina.
- Prefiere la conformidad a la configuración.

## Contribuciones

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) para obtener las directrices.

Reglas clave:
- No se pueden agregar nuevas API públicas sin actualizar `docs/public_api.md`.
- Los cambios en el esquema de eventos deben pasar una verificación de compatibilidad.
- Todas las operaciones con dinero requieren claves de idempotencia.

## Licencia

Licencia MIT. Consulte [LICENSE](LICENSE).

---

*Desarrollado por ingenieros que han sido llamados a atender emergencias a las 3 de la mañana debido a fallos silenciosos en los pagos.*
