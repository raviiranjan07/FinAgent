"""Configuration settings for FinAgent Pre-MVP."""

# =============================================================================
# RSS FEED SOURCES - URL Mapping
# =============================================================================
RSS_SOURCES = {
    # OFFICIAL - Central Banks
    "RBI_PRESS": "https://rbi.org.in/pressreleases_rss.xml",
    "FED_ALL": "https://www.federalreserve.gov/feeds/press_all.xml",
    "FED_MONETARY": "https://www.federalreserve.gov/feeds/press_monetary.xml",
    "ECB_PRESS": "https://www.ecb.europa.eu/rss/press.html",
    "BOE_NEWS": "https://www.bankofengland.co.uk/rss/news",
    "BOJ_NEWS": "https://www.boj.or.jp/en/rss/whatsnew.xml",

    # OFFICIAL - Regulators
    "SEBI": "https://www.sebi.gov.in/sebirss.xml",
    "IRDAI": "https://policyholder.gov.in/rss",  # IRDAI Policy Holder portal

    # NEWS - Global
    "BLOOMBERG_MARKETS": "https://feeds.bloomberg.com/markets/news.rss",
    "FINANCIAL_TIMES": "https://www.ft.com/rss/home",

    # NEWS - India
    "ET_MARKETS": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "ET_ECONOMY": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
    "MONEYCONTROL": "https://www.moneycontrol.com/rss/latestnews.xml",
    "LIVEMINT": "https://www.livemint.com/rss/markets",
    "BUSINESS_STANDARD": "https://www.business-standard.com/rss/markets-106.rss",

    # NEWS - US
    "CNBC_TOP": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "CNBC_WORLD": "https://www.cnbc.com/id/100727362/device/rss/rss.html",
    "MARKETWATCH": "https://feeds.marketwatch.com/marketwatch/topstories",
    "YAHOO_FINANCE": "https://finance.yahoo.com/news/rssindex",

    # GOVERNMENT - Treasury
    "TREASURY_ANNOUNCEMENTS": "https://treasurydirect.gov/TA_WS/securities/announced/rss",
    "TREASURY_AUCTIONS": "https://treasurydirect.gov/TA_WS/securities/auctioned/rss",

    # SPECIALTY - Crypto
    "COINDESK": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "COINTELEGRAPH": "https://cointelegraph.com/rss",
    "BITCOIN_MAGAZINE": "https://bitcoinmagazine.com/feed",

    # SPECIALTY - Commodities
    # "KITCO_MINING": "https://www.kitco.com/news/category/mining/rss",  # Kitco mining/gold news (DISABLED: XML parsing errors)
    "OIL_PRICE": "https://oilprice.com/rss/main",
}

# =============================================================================
# SOURCE PRIORITIZATION SYSTEM
# Hierarchical: Type → Category → Sources
# =============================================================================

SOURCE_CATEGORIES = {
    # -------------------------------------------------------------------------
    # OFFICIAL (Type) - Priority 1: Primary authoritative sources
    # -------------------------------------------------------------------------
    "CENTRAL_BANKS": {
        "type": "OFFICIAL",
        "priority": 1,
        "quota": 5,
        "region": "GLOBAL",
        "enabled": True,
        "sources": [
            "RBI_PRESS",
            "FED_ALL",
            "FED_MONETARY",
            "ECB_PRESS",
            "BOE_NEWS",
            "BOJ_NEWS",
        ],
    },
    "REGULATORS": {
        "type": "OFFICIAL",
        "priority": 1,
        "quota": 2,
        "region": "INDIA",
        "enabled": True,
        "sources": [
            "SEBI",
            "IRDAI",
        ],
    },

    # -------------------------------------------------------------------------
    # NEWS (Type) - Priority 2-3: Secondary/tertiary news sources
    # -------------------------------------------------------------------------
    "GLOBAL_NEWS": {
        "type": "NEWS",
        "priority": 2,
        "quota": 2,
        "region": "GLOBAL",
        "enabled": True,
        "sources": [
            "BLOOMBERG_MARKETS",
            "FINANCIAL_TIMES",
        ],
    },
    "INDIA_NEWS": {
        "type": "NEWS",
        "priority": 2,
        "quota": 3,
        "region": "INDIA",
        "enabled": True,
        "sources": [
            "ET_MARKETS",
            "ET_ECONOMY",
            "MONEYCONTROL",
            "LIVEMINT",
            "BUSINESS_STANDARD",
        ],
    },
    "US_NEWS": {
        "type": "NEWS",
        "priority": 3,
        "quota": 2,
        "region": "USA",
        "enabled": True,
        "sources": [
            "CNBC_TOP",
            "CNBC_WORLD",
            "MARKETWATCH",
            "YAHOO_FINANCE",
        ],
    },

    # -------------------------------------------------------------------------
    # GOVERNMENT (Type) - Priority 2: Government announcements
    # -------------------------------------------------------------------------
    "TREASURY": {
        "type": "GOVERNMENT",
        "priority": 2,
        "quota": 2,
        "region": "USA",
        "enabled": True,
        "sources": [
            "TREASURY_ANNOUNCEMENTS",
            "TREASURY_AUCTIONS",
        ],
    },

    # -------------------------------------------------------------------------
    # SPECIALTY (Type) - Priority 4: Niche/specialized sources
    # -------------------------------------------------------------------------
    "CRYPTO": {
        "type": "SPECIALTY",
        "priority": 4,
        "quota": 2,
        "region": "GLOBAL",
        "enabled": True,
        "sources": [
            "COINDESK",
            "COINTELEGRAPH",
            "BITCOIN_MAGAZINE",
        ],
    },
    "COMMODITIES": {
        "type": "SPECIALTY",
        "priority": 4,
        "quota": 2,
        "region": "GLOBAL",
        "enabled": True,
        "sources": [
            # "KITCO_MINING",  # DISABLED: XML parsing errors
            "OIL_PRICE",
        ],
    },
}

# Total quota across all categories: 19 events per run
# (reduced from 23 after removing broken feeds)


# =============================================================================
# HELPER FUNCTIONS FOR SOURCE PRIORITIZATION
# =============================================================================

def get_enabled_categories():
    """Get all enabled categories sorted by priority."""
    return sorted(
        [(name, config) for name, config in SOURCE_CATEGORIES.items() if config["enabled"]],
        key=lambda x: x[1]["priority"]
    )


def get_sources_for_category(category_name):
    """Get list of source keys for a category."""
    if category_name in SOURCE_CATEGORIES:
        return SOURCE_CATEGORIES[category_name]["sources"]
    return []


def get_category_for_source(source_key):
    """Get category name for a source key."""
    for cat_name, config in SOURCE_CATEGORIES.items():
        if source_key in config["sources"]:
            return cat_name
    return None


def get_source_url(source_key):
    """Get RSS URL for a source key."""
    return RSS_SOURCES.get(source_key)


def get_all_enabled_sources():
    """Get all source keys from enabled categories."""
    sources = []
    for config in SOURCE_CATEGORIES.values():
        if config["enabled"]:
            sources.extend(config["sources"])
    return sources


def get_total_quota():
    """Get sum of quotas from all enabled categories."""
    return sum(
        config["quota"]
        for config in SOURCE_CATEGORIES.values()
        if config["enabled"]
    )

# LLM Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"
LLM_TIMEOUT = 300  # 5 minutes
LLM_MAX_RETRIES = 3  # Number of retry attempts
LLM_RETRY_DELAY = 2  # Base delay in seconds (exponential backoff)

# Processing Configuration
MAX_EVENTS = 4
MAX_CONTENT_LENGTH = 3000  # Truncate content longer than this to prevent LLM timeout

# Event Type Categories
EVENT_TYPES = [
    "FINANCE_POLICY",
    "MARKET_INFRASTRUCTURE",
    "MARKET_MOVEMENT",
    "MACRO_ECONOMIC",
    "GEO_FINANCIAL",
    "NON_FINANCE"
]

# Content Intent Categories
CONTENT_INTENTS = [
    "EXPLANATORY",      # policy, rules, mechanisms
    "DESCRIPTIVE",      # factual reporting
    "MARKET_OPINION",   # trades, positioning, sentiment
]

# Logging
LOG_DIR = "logs"
EVENTS_LOG_FILE = "logs/events.jsonl"
EVALUATIONS_LOG_FILE = "logs/evaluations.jsonl"

# Deduplication Configuration
SIMILARITY_MODEL = "all-MiniLM-L6-v2"  # 80MB, fast, good quality
SIMILARITY_THRESHOLD = 0.85  # Cosine similarity threshold for duplicates
DEDUP_LOOKBACK_HOURS = 72  # Only compare with events from last 72 hours
