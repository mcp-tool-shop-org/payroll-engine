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

**वेतन और विनियमित वित्तीय लेनदेन के लिए एक लाइब्रेरी-आधारित पीएसपी (भुगतान सेवा प्रदाता) कोर।**

नियतात्मक, केवल जोड़ करने योग्य खाता बही। स्पष्ट फंडिंग गेट। पुनः चलाने योग्य घटनाएं। केवल सलाहकार एआई (डिफ़ॉल्ट रूप से अक्षम)। सुविधा से अधिक सटीकता।

## विश्वसनीयता के स्रोत

इस लाइब्रेरी का उपयोग करने से पहले, निम्नलिखित की समीक्षा करें:

| दस्तावेज़ | उद्देश्य |
| ---------- | --------- |
| [docs/psp_invariants.md](docs/psp_invariants.md) | सिस्टम अपरिवर्तनीय (जो गारंटीकृत है) |
| [docs/threat_model.md](docs/threat_model.md) | सुरक्षा विश्लेषण |
| [docs/public_api.md](docs/public_api.md) | सार्वजनिक एपीआई अनुबंध |
| [docs/compat.md](docs/compat.md) | संगतता गारंटी |
| [docs/adoption_kit.md](docs/adoption_kit.md) | मूल्यांकन और एम्बेडिंग गाइड |

*हम जानते हैं कि यह प्रणाली पैसे का लेनदेन करती है। ये दस्तावेज़ साबित करते हैं कि हमने इसे गंभीरता से लिया है।*

---

## यह क्यों मौजूद है

अधिकांश वेतन प्रणालियाँ पैसे के लेनदेन को एक गौण विषय मानती हैं। वे एक भुगतान एपीआई को कॉल करते हैं, सर्वोत्तम परिणाम की उम्मीद करते हैं, और विफलताओं से प्रतिक्रियाशील रूप से निपटते हैं। इससे निम्नलिखित समस्याएं उत्पन्न होती हैं:

- **अदृश्य विफलताएं**: भुगतान गायब हो जाते हैं।
- **मेल-मिलाप की दुःस्वप्न**: बैंक स्टेटमेंट रिकॉर्ड से मेल नहीं खाते।
- **देयता भ्रम**: जब वापसी होती है, तो कौन भुगतान करता है?
- **लेखा परीक्षा अंतराल**: कोई भी यह पता नहीं लगा सकता कि वास्तव में क्या हुआ।

यह परियोजना उचित वित्तीय इंजीनियरिंग के साथ पैसे के लेनदेन को एक प्राथमिक चिंता के रूप में मानकर इन समस्याओं को हल करती है।

## मुख्य सिद्धांत

### केवल जोड़ करने योग्य खाता बही क्यों महत्वपूर्ण हैं

आप एक वायर ट्रांसफर को रद्द नहीं कर सकते। आप एक ACH (इलेक्ट्रॉनिक फंड ट्रांसफर) को वापस नहीं भेज सकते। वास्तविक दुनिया केवल जोड़ करने योग्य है - इसलिए आपकी खाता बही भी उसी तरह होनी चाहिए।

```
❌ UPDATE ledger SET amount = 100 WHERE id = 1;  -- What was it before?
✅ INSERT INTO ledger (...) VALUES (...);         -- We reversed entry #1 for reason X
```

प्रत्येक संशोधन एक नई प्रविष्टि है। इतिहास संरक्षित है। लेखा परीक्षकों को खुशी होती है।

### दो फंडिंग गेट क्यों मौजूद हैं

**कमीट गेट**: "क्या हमारे पास इन भुगतानों का वादा करने के लिए पर्याप्त पैसा है?"
**पे गेट**: "क्या हमारे पास अभी भी पैसा है जब हम उन्हें भेजने वाले हैं?"

कमीट और पे के बीच का समय घंटों या दिनों तक हो सकता है। शेष राशि बदल सकती है। अन्य बैच चल सकते हैं। पे गेट अंतिम जांच बिंदु है - यह तब भी चलता है जब कोई इसे बायपास करने की कोशिश करता है।

```python
# Commit time (Monday)
psp.commit_payroll_batch(batch)  # Reservation created

# Pay time (Wednesday)
psp.execute_payments(batch)      # Pay gate checks AGAIN before sending
```

### भुगतान ≠ निपटान क्यों

"भुगतान भेजा गया" का मतलब "पैसे स्थानांतरित किए गए" नहीं है। ACH में 1-3 दिन लगते हैं। FedNow तत्काल है लेकिन फिर भी विफल हो सकता है। वायर उसी दिन होता है लेकिन महंगा है।

PSP पूरे जीवनचक्र को ट्रैक करता है:
```
Created → Submitted → Accepted → Settled (or Returned)
```

जब तक आप `Settled` नहीं देखते, तब तक आपको कोई पुष्टिकरण नहीं मिलता। जब तक आप निपटान फ़ीड को संसाधित नहीं करते, तब तक आपको यह नहीं पता कि वास्तव में क्या हुआ।

### रद्द करने के बजाय रिवर्स क्यों मौजूद हैं

जब पैसे गलत तरीके से स्थानांतरित होते हैं, तो आपको एक रिवर्स की आवश्यकता होती है - एक नई खाता बही प्रविष्टि जो मूल को ऑफसेट करती है। यह:

- लेखा परीक्षा पटरियों को संरक्षित करता है (मूल + रिवर्स)
- दिखाता है कि सुधार कब हुआ
- दस्तावेज़ करता है कि *क्यों* (वापसी कोड, कारण)

```sql
-- Original
INSERT INTO ledger (amount, ...) VALUES (1000, ...);

-- Reversal (not delete!)
INSERT INTO ledger (amount, reversed_entry_id, ...) VALUES (-1000, <original_id>, ...);
```

### आइडेंपोटेंसी क्यों अनिवार्य है

नेटवर्क विफलताएं होती हैं। पुनः प्रयास आवश्यक हैं। आइडेंपोटेंसी के बिना, आपको दोहरा भुगतान मिलता है।

PSP में प्रत्येक ऑपरेशन में एक आइडेंपोटेंसी कुंजी होती है:
```python
result = psp.commit_payroll_batch(batch)
# First call: creates reservation, returns is_new=True
# Second call: finds existing, returns is_new=False, same reservation_id
```

कॉल करने वाले को यह ट्रैक करने की आवश्यकता नहीं है कि "क्या मेरी कॉल सफल हुई?" - बस तब तक पुनः प्रयास करें जब तक आपको कोई परिणाम न मिल जाए।

## यह क्या है

एक **संदर्भ-ग्रेड पीएसपी कोर** जो निम्नलिखित के लिए उपयुक्त है:

- वेतन इंजन
- गिग अर्थव्यवस्था प्लेटफॉर्म
- लाभ प्रशासक
- ट्रेजरी प्रबंधन
- कोई भी विनियमित फिनटेक बैकएंड जो पैसे का लेनदेन करता है

## यह क्या नहीं है

यह **नहीं** है:
- एक स्ट्राइप क्लोन (कोई व्यापारी ऑनबोर्डिंग नहीं, कोई कार्ड प्रसंस्करण नहीं)
- एक वेतन SaaS (कोई कर गणना नहीं, कोई UI नहीं)
- एक डेमो या प्रोटोटाइप (उत्पादन-ग्रेड बाधाएं)

स्पष्ट गैर-लक्ष्यों के लिए [docs/non_goals.md](docs/non_goals.md) देखें।

## शुरुआत कैसे करें

```bash
# Start PostgreSQL
make up

# Apply migrations
make migrate

# Run the demo
make demo
```

यह डेमो संपूर्ण जीवनचक्र दिखाता है:
1. किरायेदार (tenant) और खाते बनाएं
2. खाते में धन जमा करें
3. वेतन बैच (भुगतान) आरक्षित करें
4. भुगतान निष्पादित करें
5. निपटान (settlement) फीड का अनुकरण करें
6. देयता वर्गीकरण के साथ वापसी (return) को संभालें
7. घटनाओं को पुनः चलाएं

## लाइब्रेरी का उपयोग

PSP एक सेवा नहीं, बल्कि एक लाइब्रेरी है। इसका उपयोग अपने एप्लिकेशन के अंदर करें:

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

## दस्तावेज़

| दस्तावेज़ | उद्देश्य |
| ---------- | --------- |
| [docs/public_api.md](docs/public_api.md) | सार्वजनिक एपीआई अनुबंध (जो स्थिर है) |
| [docs/compat.md](docs/compat.md) | संस्करण और अनुकूलता |
| [docs/psp_invariants.md](docs/psp_invariants.md) | सिस्टम की अपरिवर्तनीयता (जो गारंटीकृत है) |
| [docs/idempotency.md](docs/idempotency.md) | आइडेंपोटेंसी पैटर्न |
| [docs/threat_model.md](docs/threat_model.md) | सुरक्षा विश्लेषण |
| [docs/non_goals.md](docs/non_goals.md) | PSP क्या नहीं करता |
| [docs/upgrading.md](docs/upgrading.md) | अपग्रेड और माइग्रेशन गाइड |
| [docs/runbooks/](docs/runbooks/) | परिचालन प्रक्रियाएं |
| [docs/recipes/](docs/recipes/) | एकीकरण उदाहरण |

## एपीआई स्थिरता का वादा

**स्थिर (बगैर किसी प्रमुख संस्करण के नहीं बदलेगा):**
- `payroll_engine.psp` - PSP फ़ेसड और कॉन्फ़िगरेशन
- `payroll_engine.psp.providers` - प्रदाता प्रोटोकॉल
- `payroll_engine.psp.events` - डोमेन इवेंट
- `payroll_engine.psp.ai` - एआई सलाह (कॉन्फ़िगरेशन और सार्वजनिक प्रकार)

**आंतरिक (सूचना दिए बिना बदल सकता है):**
- `payroll_engine.psp.services.*` - कार्यान्वयन विवरण
- `payroll_engine.psp.ai.models.*` - मॉडल आंतरिक
- किसी भी चीज़ में `_` उपसर्ग

**एआई सलाह की सीमाएं (लागू):**
- पैसे नहीं ले जा सकते
- लेज़र प्रविष्टियाँ नहीं लिख सकते
- फंडिंग गेट को ओवरराइड नहीं कर सकते
- निपटान निर्णय नहीं ले सकते
- केवल सलाहकार इवेंट उत्सर्जित करते हैं

पूरे अनुबंध के लिए [docs/public_api.md](docs/public_api.md) देखें।

## मुख्य गारंटी

| गारंटी | कार्यान्वयन |
| ----------- | ------------- |
| पैसे हमेशा सकारात्मक होते हैं | `CHECK (amount > 0)` |
| कोई स्व-स्थानांतरण नहीं | `CHECK (debit != credit)` |
| लेज़र केवल अपेंड-ओनली है | प्रविष्टियों पर कोई UPDATE/DELETE नहीं |
| स्थिति केवल आगे बढ़ती है | ट्रिगर संक्रमण को मान्य करता है |
| घटनाएं अपरिवर्तनीय हैं | CI में स्कीमा संस्करण |
| पे गेट को बाईपास नहीं किया जा सकता | फ़ेसड में लागू |
| एआई पैसे नहीं ले जा सकता | वास्तुशिल्पीय बाधा |

## सीएलआई उपकरण

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

## स्थापना

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

## वैकल्पिक निर्भरताएँ

PSP को सख्त वैकल्पिकता के साथ डिज़ाइन किया गया है। **मुख्य धन हस्तांतरण के लिए शून्य वैकल्पिक निर्भरता की आवश्यकता होती है।**

| Extra | यह क्या जोड़ता है | डिफ़ॉल्ट स्थिति |
| ------- | -------------- | --------------- |
| `[ai]` | एमएल-आधारित एआई मॉडल (भविष्य) | नियम-आधारित के लिए आवश्यक नहीं |
| `[crypto]` | ब्लॉकचेन एकीकरण (भविष्य) | **OFF** - reserved for future |
| `[postgres]` | पोस्टग्रेएसक्यूएल ड्राइवर | केवल उपयोग किए जाने पर लोड होता है |
| `[asyncpg]` | एसिंक्रोनस पोस्टग्रेएसक्यूएल | केवल उपयोग किए जाने पर लोड होता है |

### एआई सलाह: दो-स्तरीय प्रणाली

**नियम-आधारित एआई किसी भी अतिरिक्त के बिना काम करता है।** आपको ये मिलते हैं:
- जोखिम स्कोरिंग
- वापसी विश्लेषण
- रनबुक सहायता
- प्रति-तथ्यात्मक सिमुलेशन
- किरायेदार जोखिम प्रोफाइलिंग

यह सब stdlib से परे शून्य निर्भरता के साथ।

```python
from payroll_engine.psp.ai import AdvisoryConfig, ReturnAdvisor

# Rules-baseline needs NO extras - just enable it
config = AdvisoryConfig(enabled=True, model_name="rules_baseline")
```

**एमएल मॉडल (भविष्य) के लिए `[ai]` अतिरिक्त की आवश्यकता होती है:**

```python
# Only needed for ML models, not rules-baseline
pip install payroll-engine[ai]

# Then use ML models
config = AdvisoryConfig(enabled=True, model_name="gradient_boost")
```

### एआई सलाह की सीमाएं (लागू)

सभी एआई सुविधाएँ **कभी भी**:
- पैसे नहीं ले जा सकते
- लेज़र प्रविष्टियाँ नहीं लिख सकते
- फंडिंग गेट को ओवरराइड नहीं कर सकते
- निपटान निर्णय नहीं ले सकते

एआई केवल मानव/नीति समीक्षा के लिए सलाहकार इवेंट उत्सर्जित करता है।

वैकल्पिकता तालिका के लिए [docs/public_api.md](docs/public_api.md) देखें।

## परीक्षण

```bash
# Unit tests
make test

# With database
make test-psp

# Red team tests (constraint verification)
pytest tests/psp/test_red_team_scenarios.py -v
```

## इसका उपयोग कौन करना चाहिए

**PSP का उपयोग करें यदि आप:**
- विनियमित परिस्थितियों में धन का हस्तांतरण करते हैं।
- आपको ऐसे ऑडिट रिकॉर्ड की आवश्यकता है जो अनुपालन आवश्यकताओं को पूरा करते हों।
- आप सुविधा से अधिक सटीकता को महत्व देते हैं।
- आपने 3 बजे भुगतान विफल होने की स्थिति को संभाला है।

**PSP का उपयोग न करें यदि आप:**
- स्ट्राइप का एक आसान विकल्प चाहते हैं।
- आपको एक पूर्ण वेतन समाधान की आवश्यकता है।
- आप कॉन्फ़िगरेशन की तुलना में पारंपरिक तरीकों को पसंद करते हैं।

## योगदान

मार्गदर्शिका के लिए [CONTRIBUTING.md](CONTRIBUTING.md) देखें।

मुख्य नियम:
- `docs/public_api.md` को अपडेट किए बिना कोई नया सार्वजनिक एपीआई नहीं।
- इवेंट स्कीमा में बदलाव संगतता जांच पास करना चाहिए।
- सभी मौद्रिक लेनदेन के लिए idempotency कुंजी की आवश्यकता होती है।

## लाइसेंस

एमआईटी लाइसेंस। [LICENSE](LICENSE) देखें।

---

*इंजीनियरों द्वारा बनाया गया है जिन्होंने भुगतान विफल होने पर चुपचाप 3 बजे 'पेज' किया गया है।*
