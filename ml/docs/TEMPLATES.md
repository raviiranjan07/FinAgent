# Template Syntax for Synthetic Data Generation

This document explains how templates are used to generate synthetic training data.

---

## Overview

Templates are sentence patterns with placeholders that get filled randomly to create diverse training samples.

```python
# Template
"{regulator} announces new {policy_type} for {sector}"

# Generated samples
"RBI announces new lending guidelines for banking sector"
"SEBI announces new capital requirements for NBFCs"
"Federal Reserve announces new risk framework for insurance companies"
```

---

## Template Syntax

### Basic Placeholder

```python
"{placeholder_name}"
```

Placeholders are enclosed in curly braces and match keys in the `PLACEHOLDERS` dictionary.

### Example

```python
TEMPLATES = {
    "FINANCE_POLICY": [
        "{regulator} announces new {policy_type} for {sector}",
    ]
}

PLACEHOLDERS = {
    "regulator": ["RBI", "SEBI", "Federal Reserve"],
    "policy_type": ["lending guidelines", "capital requirements"],
    "sector": ["banking sector", "NBFCs", "insurance companies"],
}
```

---

## Placeholder Definitions by Category

### FINANCE_POLICY

| Placeholder | Values |
|-------------|--------|
| `regulator` | RBI, SEBI, Federal Reserve, ECB, SEC, CFTC, FCA, MAS, BOE, BOJ |
| `policy_type` | lending guidelines, capital requirements, risk framework, monetary policy, liquidity norms |
| `sector` | banking sector, NBFCs, insurance companies, mutual funds, fintech |
| `action` | issues, announces, releases, implements, enforces |
| `enforcement` | penalty, fine, warning, suspension, ban |
| `violation` | insider trading, market manipulation, disclosure violations, compliance failures |

### DIGITAL_ASSETS

| Placeholder | Values |
|-------------|--------|
| `crypto` | Bitcoin, Ethereum, Solana, XRP, Cardano, Dogecoin, Polygon, Avalanche |
| `exchange` | Binance, Coinbase, Kraken, WazirX, CoinDCX, Gemini, FTX, Bybit |
| `price_action` | rallies, surges, drops, plummets, soars, gains, loses, stabilizes |
| `event` | ETF approval, network upgrade, halving, institutional adoption, regulatory news |
| `feature` | staking, lending, futures trading, margin trading, custody |
| `defi_term` | DeFi protocol, liquidity pool, yield farming, staking rewards, smart contract |

### MARKET_INFRASTRUCTURE

| Placeholder | Values |
|-------------|--------|
| `exchange` | NSE, BSE, NYSE, NASDAQ, LSE, SGX, HKEX, TSE |
| `instrument` | bonds, treasury bills, government securities, corporate bonds, municipal bonds |
| `operation` | trading, clearing, settlement, auction, listing |
| `issue` | technical glitch, system outage, circuit breaker, halt |
| `partnership` | MOU, collaboration, cross-listing, data sharing |

### MARKET_MOVEMENT

| Placeholder | Values |
|-------------|--------|
| `market` | stocks, shares, equities, markets, indices |
| `movement` | rally, selloff, surge, plunge, sink, rise, fall, climb |
| `sentiment` | risk sentiment, investor confidence, market optimism, bearish mood |
| `trigger` | earnings, jobs data, Fed decision, inflation report, GDP data |
| `sector` | tech shares, banking stocks, energy sector, pharma stocks |

### MACRO_ECONOMIC

| Placeholder | Values |
|-------------|--------|
| `indicator` | inflation, GDP, unemployment, CPI, PPI, retail sales, industrial output |
| `body` | FOMC, RBI MPC, ECB, BOE, BOJ |
| `rate_action` | holds, raises, cuts, maintains, increases, decreases |
| `rate_amount` | 25 basis points, 50 basis points, 75 basis points, 0.25%, 0.5% |
| `economic_state` | growth, contraction, recession, expansion, slowdown |

### GEO_FINANCIAL

| Placeholder | Values |
|-------------|--------|
| `currency` | dollar, euro, yen, rupee, pound, yuan |
| `currency_action` | strengthens, weakens, depreciates, appreciates, stabilizes |
| `geo_event` | tariffs, sanctions, trade war, conflict, tensions |
| `country` | US, China, Russia, EU, Japan, India, UK |
| `commodity` | oil, gas, energy, crude, natural gas |
| `intervention` | intervenes, supports, defends, sells, buys |

### SKIP

| Placeholder | Values |
|-------------|--------|
| `case_number` | 1234, 5678, 9012, 3456, 7890 |
| `year` | 2023, 2024, 2025 |
| `person_name` | Sharma, Gupta, Patel, Kumar, Singh, Mehta |
| `question_word` | Should, Can, Will, Do, Does |
| `investment` | mutual funds, stocks, bonds, real estate, gold |

### NON_FINANCE

| Placeholder | Values |
|-------------|--------|
| `tech_company` | Apple, Google, Microsoft, Amazon, Meta |
| `product` | iPhone, smartphone, tablet, laptop, AI assistant |
| `sport` | cricket, football, tennis, basketball |
| `team` | India, Australia, England, Spain |
| `event_type` | launches, announces, releases, unveils |

---

## Template Examples by Category

### FINANCE_POLICY Templates

```python
[
    "{regulator} announces new {policy_type} for {sector}",
    "{regulator} {action} {enforcement} on {violation}",
    "New {policy_type} regulation by {regulator} affects {sector}",
    "{regulator} tightens {policy_type} amid market concerns",
    "{enforcement} imposed by {regulator} for {violation}",
    "{regulator} releases draft {policy_type} for public comment",
    "Government introduces new scheme for {sector}",
    "{regulator} enforcement action targets {violation}",
]
```

### DIGITAL_ASSETS Templates

```python
[
    "{crypto} {price_action} as {event} unfolds",
    "{exchange} launches {feature} for {crypto} trading",
    "{crypto} hits new high amid {event}",
    "{defi_term} sees record activity on {crypto} network",
    "{exchange} faces regulatory scrutiny over {feature}",
    "Institutional investors increase {crypto} holdings",
    "{crypto} network upgrade improves {feature}",
    "NFT marketplace reports surge in {crypto} transactions",
]
```

### MARKET_INFRASTRUCTURE Templates

```python
[
    "{exchange} {operation} halted due to {issue}",
    "Treasury {instrument} auction sees strong demand",
    "{exchange} signs {partnership} with international exchange",
    "{exchange} introduces new {operation} framework",
    "Government {instrument} yield rises to record high",
    "{exchange} to extend {operation} hours",
    "Clearing corporation updates margin requirements for {instrument}",
]
```

### MARKET_MOVEMENT Templates

```python
[
    "{market} {movement} as {trigger} disappoints",
    "{sentiment} improves amid positive {trigger}",
    "{sector} {movement} on strong quarterly results",
    "Global {market} {movement} continues for third day",
    "{market} hit all-time high amid buying",
    "{sector} leads {movement} on {trigger}",
    "Investors dump {market} as {sentiment} worsens",
]
```

### MACRO_ECONOMIC Templates

```python
[
    "{indicator} hits multi-year high at record level",
    "{body} {rate_action} interest rate by {rate_amount}",
    "{indicator} data shows economic {economic_state}",
    "{body} signals rate changes in coming months",
    "Unemployment rate drops as economy shows {economic_state}",
    "{indicator} rises faster than expected",
    "{body} maintains hawkish stance on {indicator}",
]
```

### GEO_FINANCIAL Templates

```python
[
    "{country} imposes new {geo_event} on imports",
    "{currency} {currency_action} as {geo_event} tensions escalate",
    "{commodity} prices surge amid {country} {geo_event}",
    "{country} {intervention} to support weakening {currency}",
    "{geo_event} impact {currency} and energy markets",
    "{currency} depreciates to record low against {currency}",
    "{country} {geo_event} affect global supply chains",
]
```

### SKIP Templates

```python
[
    "Appeal No. {case_number} of {year} filed by {person_name}",
    "Order in the matter of {person_name} vs {regulator}",
    "{question_word} I invest in {investment} now?",
    "My neighbor inherited money. {question_word} he invest in {investment}?",
    "{question_word} you recommend a good {investment} to buy?",
    "I'm planning to retire. {question_word} I sell my {investment}?",
]
```

### NON_FINANCE Templates

```python
[
    "{tech_company} {event_type} new {product} with AI features",
    "Scientists discover breakthrough in research",
    "{team} wins {sport} championship",
    "New restaurant opens in major city",
    "Prime Minister visits affected areas",
    "{tech_company} announces quarterly earnings",
]
```

---

## Adding New Templates

### Guidelines

1. **Ensure diversity:** Each template should generate meaningfully different samples
2. **Use appropriate placeholders:** Match placeholders to the category
3. **Maintain natural language:** Templates should read like real headlines
4. **Avoid overlap:** Don't create templates that could belong to multiple categories

### Process

1. Add template to `ml/data/templates.py` under the appropriate category
2. Add any new placeholders to the `PLACEHOLDERS` dictionary
3. Regenerate training data: `python -m ml.data.generator`
4. Retrain model: `python -m ml.train`

### Example: Adding a new FINANCE_POLICY template

```python
# In ml/data/templates.py

TEMPLATES["FINANCE_POLICY"].append(
    "{regulator} proposes new {policy_type} for {sector} oversight"
)

# If using a new placeholder, add it:
PLACEHOLDERS["oversight_type"] = ["prudential", "conduct", "systemic"]
```

---

## Variation Techniques

The generator applies these variations to increase diversity:

1. **Case variation:** Random title case, lowercase, uppercase
2. **Punctuation:** Optional trailing periods
3. **Word order:** Some templates have alternate orderings
4. **Synonym substitution:** Built into placeholder values

```python
# Original
"RBI announces new lending guidelines for NBFCs"

# Variations generated
"rbi announces new lending guidelines for nbfcs"
"RBI Announces New Lending Guidelines For NBFCs"
"RBI announces new lending guidelines for NBFCs."
```
