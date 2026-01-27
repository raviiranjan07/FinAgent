# Event Categories Reference

This document defines the 8 event categories used by the ML classifier.

---

## 1. FINANCE_POLICY

**Description:** Regulatory announcements, central bank policies, enforcement actions, and government financial schemes.

**Key Entities:**
- Regulators: RBI, SEBI, Federal Reserve, ECB, SEC, CFTC, FCA, MAS
- Actions: regulation, policy, guidelines, enforcement, penalty, scheme, act

**Example Headlines:**
| Headline | Why FINANCE_POLICY |
|----------|-------------------|
| "RBI announces new lending guidelines for NBFCs" | Central bank + regulatory action |
| "SEBI penalizes broker for insider trading violations" | Regulator + enforcement |
| "Federal Reserve signals tighter monetary controls" | Central bank + policy |
| "Government launches new pension scheme for unorganized sector" | Government + financial scheme |
| "ECB introduces stricter capital requirements for banks" | Central bank + regulation |
| "SEC charges company with securities fraud" | Regulator + enforcement |

**Keywords:** rbi, sebi, regulation, policy, act, scheme, federal reserve, enforcement action, ecb, central bank, sec, cftc, guidelines, penalty

---

## 2. DIGITAL_ASSETS

**Description:** Cryptocurrency, blockchain technology, NFTs, DeFi, crypto exchanges, and related digital asset news.

**Key Entities:**
- Cryptocurrencies: Bitcoin, Ethereum, Solana, XRP, Cardano, Dogecoin
- Exchanges: Binance, Coinbase, Kraken, WazirX, CoinDCX
- Concepts: blockchain, DeFi, NFT, staking, mining, wallet, token

**Example Headlines:**
| Headline | Why DIGITAL_ASSETS |
|----------|-------------------|
| "Bitcoin rallies past $100K on ETF approval news" | Major crypto + price movement |
| "Ethereum staking rewards increase after network upgrade" | Crypto + DeFi concept |
| "Binance faces regulatory scrutiny in multiple countries" | Crypto exchange |
| "NFT marketplace OpenSea reports record trading volume" | NFT platform |
| "Solana network experiences outage affecting DeFi protocols" | Blockchain + DeFi |
| "Coinbase launches institutional custody service" | Crypto exchange + service |

**Keywords:** crypto, cryptocurrency, bitcoin, ethereum, blockchain, etf, staking, defi, nft, digital asset, web3, altcoin, token, mining, wallet, binance, coinbase, solana, cardano, ripple, xrp

---

## 3. MARKET_INFRASTRUCTURE

**Description:** Stock exchanges, commodity exchanges, bond markets, treasury operations, clearing systems, and market infrastructure.

**Key Entities:**
- Exchanges: NSE, BSE, NYSE, NASDAQ, LSE, SGX
- Instruments: bonds, treasury bills, government securities
- Operations: auction, clearing, settlement, MOU

**Example Headlines:**
| Headline | Why MARKET_INFRASTRUCTURE |
|----------|--------------------------|
| "NSE trading halted due to technical glitch" | Stock exchange + operations |
| "Treasury bond auction sees record demand from investors" | Treasury + auction |
| "BSE signs MOU with Singapore Exchange for cross-listing" | Exchange + partnership |
| "NSCCL introduces new margin framework for derivatives" | Clearing house + operations |
| "Government securities yield rises to 7.5%" | Bond market |
| "NYSE to extend trading hours for select securities" | Exchange + operations |

**Keywords:** stock exchange, commodity exchange, nse, bse, nyse, nasdaq, bond, treasury, bill, auction, mou, clearing, settlement

---

## 4. MARKET_MOVEMENT

**Description:** Stock market price movements, trading sentiment, market rallies/selloffs, and general market activity.

**Key Entities:**
- Markets: stocks, shares, indices, equities
- Movements: rally, selloff, surge, plunge, sink
- Sentiment: risk-on, risk-off, bullish, bearish

**Example Headlines:**
| Headline | Why MARKET_MOVEMENT |
|----------|---------------------|
| "Stocks sink as weak earnings disappoint investors" | Price movement + sentiment |
| "Markets rally on positive jobs data" | Market + upward movement |
| "Risk sentiment improves as trade tensions ease" | Market sentiment |
| "Nifty hits all-time high amid FII buying" | Index + price movement |
| "Global equities selloff continues for third day" | Market + downward movement |
| "Tech shares surge on AI optimism" | Sector + price movement |

**Keywords:** stocks, shares, markets, selloff, sink, rally, risk sentiment, trades, surge, plunge, equities, bullish, bearish

---

## 5. MACRO_ECONOMIC

**Description:** Macroeconomic indicators, monetary policy decisions, inflation data, GDP reports, and interest rate changes.

**Key Entities:**
- Indicators: inflation, GDP, unemployment, CPI, PPI
- Policy: interest rate, monetary policy, rate decision
- Bodies: FOMC, MPC, central bank committees

**Example Headlines:**
| Headline | Why MACRO_ECONOMIC |
|----------|-------------------|
| "Inflation hits 5-year high at 6.2%" | Economic indicator |
| "FOMC holds interest rate steady at 5.25-5.50%" | Monetary policy decision |
| "GDP growth slows to 4.5% in Q3" | Economic indicator |
| "RBI MPC cuts repo rate by 25 basis points" | Monetary policy + rate decision |
| "Unemployment rate drops to 3.7% in December" | Economic indicator |
| "Federal Reserve signals rate cuts in 2025" | Monetary policy outlook |

**Keywords:** inflation, gdp, interest rate, liquidity, money supply, fomc, federal open market, discount rate, federal funds, monetary policy, rate decision, basis points, cpi, unemployment

---

## 6. GEO_FINANCIAL

**Description:** Geopolitical events affecting finance, trade wars, sanctions, forex movements, currency interventions, and energy/oil markets.

**Key Entities:**
- Currencies: USD, EUR, JPY, INR, GBP, CNY
- Geopolitical: tariffs, sanctions, trade war, conflict
- Commodities: oil, energy, gas

**Example Headlines:**
| Headline | Why GEO_FINANCIAL |
|----------|-------------------|
| "US imposes new tariffs on Chinese imports" | Trade policy |
| "Dollar strengthens as trade war tensions escalate" | Currency + geopolitics |
| "Oil prices surge amid Middle East conflict" | Commodity + geopolitics |
| "Japan intervenes to support weakening yen" | Currency intervention |
| "EU sanctions Russian energy exports" | Sanctions + energy |
| "Rupee depreciates to record low against dollar" | Currency movement |

**Keywords:** tariff, sanction, trade war, oil, energy supply, conflict, yen, dollar, euro, currency, forex, foreign exchange, intervention, exchange rate, depreciation, appreciation, weaken, strengthen

---

## 7. NON_FINANCE

**Description:** Valid news articles that don't fit any financial category. Used as a fallback when classifier confidence is below threshold.

**Characteristics:**
- Legitimate news content
- Not financial in nature
- May be tech, science, sports, politics, lifestyle

**Example Headlines:**
| Headline | Why NON_FINANCE |
|----------|-----------------|
| "Apple launches new iPhone with AI features" | Tech (not crypto/finance) |
| "Scientists discover high-temperature superconductor" | Science |
| "India wins cricket World Cup final" | Sports |
| "New restaurant opens in Mumbai" | Lifestyle |
| "Prime Minister visits flood-affected areas" | General politics |

**Usage:** Articles classified as NON_FINANCE may be stored but typically won't trigger content generation.

---

## 8. SKIP

**Description:** Content that should be filtered out entirely - administrative, legal, personal advice columns.

**Characteristics:**
- Legal case filings and appeals
- Enforcement orders (detailed legal documents)
- Personal finance Q&A columns
- Advice-seeking content

**Detection:** Rule-based regex patterns (not ML)

**Skip Patterns:**
```python
SKIP_PATTERNS = [
    r"appeal\s+no\.\s*\d+",           # "Appeal No. 6674"
    r"appeal\s+nos?\.\s*\d+",         # "Appeal Nos. 6670 & 6671"
    r"filed\s+by\s+[A-Z][a-z]+",      # "filed by Sharma"
    r"order\s+in\s+the\s+matter\s+of", # Legal orders
    r"^(my|i'm|i am|we're|we are)\s+", # Personal stories
    r"\?\s*$",                        # Ends with question
    r"(should|can|will|do|does)\s+(i|you|we)\s+", # Advice seeking
]
```

**Example Content:**
| Content | Why SKIP |
|---------|----------|
| "Appeal No. 6674 of 2024 filed by Sharma vs SEBI" | Legal filing |
| "Order in the matter of XYZ Ltd - SEBI enforcement" | Legal document |
| "Should I invest in mutual funds for my child's education?" | Personal advice Q&A |
| "My neighbor inherited Rs 50 lakh. What should he do?" | Personal advice |
| "Can you recommend a good stock to buy now?" | Advice seeking |

---

## Category Selection Logic

```
1. Check SKIP patterns (rule-based) → If match → SKIP
2. Generate embedding (MiniLM)
3. Run classifier → Get probabilities for all categories
4. If max probability < 0.55 → NON_FINANCE
5. Else → Primary category = highest probability
6. If second highest > 0.40 → Secondary category
```

## Multi-Category Examples

Some articles may span multiple categories:

| Headline | Primary | Secondary |
|----------|---------|-----------|
| "RBI discusses crypto regulation framework" | FINANCE_POLICY | DIGITAL_ASSETS |
| "Oil sanctions impact forex markets" | GEO_FINANCIAL | MACRO_ECONOMIC |
| "Fed rate decision impacts stock markets" | MACRO_ECONOMIC | MARKET_MOVEMENT |
| "NSE launches Bitcoin futures trading" | MARKET_INFRASTRUCTURE | DIGITAL_ASSETS |
