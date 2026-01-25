"""Configuration settings for FinAgent application."""

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

    # NEWS - Global
    "BLOOMBERG_MARKETS": "https://feeds.bloomberg.com/markets/news.rss",
    "FINANCIAL_TIMES": "https://www.ft.com/rss/home",

    # NEWS - India
    "ET_MARKETS": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "ET_ECONOMY": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
    "MONEYCONTROL": "https://www.moneycontrol.com/rss/latestnews.xml",
    "LIVEMINT": "https://www.livemint.com/rss/markets",

    # NEWS - US
    "CNBC_TOP": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "CNBC_WORLD": "https://www.cnbc.com/id/100727362/device/rss/rss.html",
    "MARKETWATCH": "https://feeds.marketwatch.com/marketwatch/topstories",
    "YAHOO_FINANCE": "https://finance.yahoo.com/news/rssindex",

    # SPECIALTY - Crypto
    "COINDESK": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "COINTELEGRAPH": "https://cointelegraph.com/rss",
    "BITCOIN_MAGAZINE": "https://bitcoinmagazine.com/feed",
    "INVESTING_CRYPTO": "https://in.investing.com/rss/news_301.rss",

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
        ],
    },

    # -------------------------------------------------------------------------
    # NEWS (Type) - Priority 2-3: Secondary/tertiary news sources
    # -------------------------------------------------------------------------
    "GLOBAL_NEWS": {
        "type": "NEWS",
        "priority": 2,
        "quota": 5,
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
        "quota": 4,
        "region": "INDIA",
        "enabled": True,
        "sources": [
            "ET_MARKETS",
            "ET_ECONOMY",
            "MONEYCONTROL",
            "LIVEMINT",
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
            "INVESTING_CRYPTO",
        ],
    },
}


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

# =============================================================================
# LLM Configuration
# =============================================================================
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# LLM Mode: "openrouter", "gemini", or "ollama"
LLM_MODE = os.getenv("LLM_MODE", "ollama").lower()

# Ollama Configuration (when LLM_MODE=ollama)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-minilm")

# Groq API Configuration (when LLM_MODE=groq)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Google Gemini API Configuration (dual model support)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")  # Legacy setting (kept for compatibility)
GEMINI_PRIMARY_MODEL = os.getenv("GEMINI_PRIMARY_MODEL", "gemini-2.5-flash-preview-09-202")
GEMINI_SECONDARY_MODEL = os.getenv("GEMINI_SECONDARY_MODEL", "gemini-2.5-flash")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")

# General LLM Settings (applies to both modes)
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_RETRY_DELAY = int(os.getenv("LLM_RETRY_DELAY", "2"))

# Fallback configuration
# Fallback chain: Groq → Gemini → Ollama
LLM_ENABLE_GEMINI_FALLBACK = os.getenv("LLM_ENABLE_GEMINI_FALLBACK", "true").lower() == "true"
LLM_ENABLE_OLLAMA_FALLBACK = os.getenv("LLM_ENABLE_OLLAMA_FALLBACK", "true").lower() == "true"

# Legacy compatibility (for old code that uses MODEL_NAME)
MODEL_NAME = OLLAMA_MODEL

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

# =============================================================================
# Operational Safety Configuration (Kill Switch + Versioning)
# =============================================================================

# Kill Switch: Emergency controls to disable generation/publishing without code deployment
CONTENT_GENERATION_ENABLED = os.getenv("CONTENT_GENERATION_ENABLED", "true").lower() == "true"
# Note: PUBLISHING_ENABLED removed - use TWITTER_PUBLISHING_ENABLED instead (line 370)

# Prompt Versioning: Track prompt versions for audit trail
PROMPT_VERSION = "1.0"
TWITTER_PROMPT_VERSION = "1.7-rpm"  # RPM optimization: soft tension, smart hashtags, engagement focus

# Note: These can be toggled via environment variables or API endpoints
# CONTENT_GENERATION_ENABLED: Set to "false" to stop pipeline content generation
# TWITTER_PUBLISHING_ENABLED: Set to "false" to stop Twitter publishing (see line 370)

# =============================================================================
# Twitter Plugin Configuration
# =============================================================================

# Twitter tier from environment (FREE or PREMIUM)
TWITTER_TIER = os.getenv("TWITTER_TIER", "FREE")

# Tier-specific capabilities
TWITTER_TIERS = {
    "FREE": {
        "max_single_tweet": 280,
        "optimal_thread_length": 3,
        "description": "Free tier - 280 char tweets, 3-tweet threads"
    },
    "PREMIUM": {
        "max_single_tweet": 4000,
        "optimal_thread_length": 3,
        "description": "Premium tier - 4000 char tweets (future)"
    }
}

# Get current tier config
TWITTER_CONFIG = TWITTER_TIERS.get(TWITTER_TIER, TWITTER_TIERS["FREE"])

# Twitter plugin execution mode
TWITTER_PLUGIN_ENABLED = os.getenv("TWITTER_PLUGIN_ENABLED", "false").lower() == "true"

# =============================================================================
# Twitter Content Generation LLM Configuration
# =============================================================================
# Separate LLM configuration for Twitter content generation
# This allows using different (cheaper/faster) models for Twitter vs main pipeline

# Twitter content generation mode (defaults to main LLM_MODE if not set)
TWITTER_CONTENT_MODE = os.getenv("TWITTER_CONTENT_MODE", LLM_MODE).lower()

# Twitter content model (generic, not provider-specific)
# Defaults to the appropriate main pipeline model based on TWITTER_CONTENT_MODE
TWITTER_CONTENT_MODEL = os.getenv("TWITTER_CONTENT_MODEL", "")

# Twitter LLM settings (uses main pipeline settings by default)
TWITTER_LLM_TIMEOUT = int(os.getenv("TWITTER_LLM_TIMEOUT", str(LLM_TIMEOUT)))
TWITTER_LLM_MAX_RETRIES = int(os.getenv("TWITTER_LLM_MAX_RETRIES", str(LLM_MAX_RETRIES)))

# =============================================================================
# Twitter API v2 Configuration (Phase 3: Publishing)
# =============================================================================

# Twitter API v2 credentials (OAuth 1.0a User Context)
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")

# Publishing controls
TWITTER_PUBLISHING_ENABLED = os.getenv("TWITTER_PUBLISHING_ENABLED", "false").lower() == "true"
TWITTER_DRY_RUN = os.getenv("TWITTER_DRY_RUN", "true").lower() == "true"

# Validate Twitter credentials
def validate_twitter_credentials():
    """Check if Twitter API credentials are configured."""
    required = [
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_TOKEN_SECRET
    ]
    return all(cred for cred in required)

# Twitter API rate limits (Free tier)
TWITTER_RATE_LIMIT_TWEETS_PER_DAY = 50
TWITTER_RATE_LIMIT_TWEETS_PER_15MIN = 17
