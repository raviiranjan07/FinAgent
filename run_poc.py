import uuid
import os
import time
import json
import datetime
import feedparser
import requests
from pydantic import BaseModel

os.makedirs("logs", exist_ok=True)

# -----------------------------
# CONFIG
# -----------------------------

RSS_SOURCES = {
   "BLOOMBERG_MARKETS": "https://feeds.bloomberg.com/markets/news.rss",
    "RBI_PRESS": "https://rbi.org.in/pressreleases_rss.xml",
    # "REUTERS_BUSINESS": "https://feeds.reuters.com/reuters/businessNews",
}

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"

MAX_EVENTS = 10

SYSTEM_PROMPT = """
You are a finance content explainer.

Rules:
- Do NOT give advice.
- Do NOT predict future outcomes.
- Do NOT assume reader expertise.
- Explain all financial terms in simple language.
- Keep it concise and factual.
"""

EVENT_TYPES = [
    "FINANCE_POLICY",
    "MARKET_INFRASTRUCTURE",
    "MARKET_MOVEMENT",
    "MACRO_ECONOMIC",
    "GEO_FINANCIAL",
    "NON_FINANCE"
]


CONTENT_INTENT = [
    "EXPLANATORY",      # policy, rules, mechanisms
    "DESCRIPTIVE",      # factual reporting
    "MARKET_OPINION",   # trades, positioning, sentiment
]


# -----------------------------
# SCHEMA
# -----------------------------

class Event(BaseModel):
    event_id: str
    source: str
    title: str
    published_at: str
    raw_text: str

# -----------------------------
# FETCHER
# -----------------------------

def fetch_events(source_name, url):
    feed = feedparser.parse(url)
    events = []

    for entry in feed.entries[:MAX_EVENTS]:
        events.append(Event(
            event_id=str(uuid.uuid4()),
            source=source_name,
            title=entry.get("title", ""),
            published_at=entry.get("published", ""),
            raw_text=entry.get("summary", "")
        ))
    print("Entries found:", len(feed.entries))
    return events

# -----------------------------
# LLM GENERATOR
# -----------------------------

def generate_explanation(event: Event, intent: str):
    if intent == "EXPLANATORY":
        task = "Explain the concept, process, and who it affects in simple terms."

    elif intent == "MARKET_OPINION":
        task = "Summarize who is saying what and why, without giving advice or predictions."

    else:  # DESCRIPTIVE
        task = "Briefly summarize what happened, focusing only on facts."

    prompt = f"""
SYSTEM:
{SYSTEM_PROMPT}

EVENT TITLE:
{event.title}

EVENT CONTENT:
{event.raw_text}

TASK:
{task}
"""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)  # Increased timeout to 5 minutes
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        print(f"LLM generation failed for event {event.event_id}: {e}")
        return f"Error: Could not generate explanation due to LLM timeout or error."

# -----------------------------
# EVENT CLASSIFIER  
# -----------------------------

def classify_event(title: str, text: str) -> str:
    combined = f"{title} {text}".lower()

    # Policy & regulation
    if any(k in combined for k in [
        "rbi", "sebi", "regulation", "policy", "act", "scheme"
    ]):
        return "FINANCE_POLICY"

    # Market plumbing / instruments
    if any(k in combined for k in [
        "exchange", "bond", "treasury", "bill",
        "auction", "mou", "clearing"
    ]):
        return "MARKET_INFRASTRUCTURE"

    # Market price action / sentiment
    if any(k in combined for k in [
        "stocks", "shares", "markets", "selloff",
        "sink", "rally", "risk sentiment", "trades"
    ]):
        return "MARKET_MOVEMENT"

    # Macro signals
    if any(k in combined for k in [
        "inflation", "gdp", "interest rate",
        "liquidity", "money supply"
    ]):
        return "MACRO_ECONOMIC"

    # Geopolitics affecting finance
    if any(k in combined for k in [
        "tariff", "sanction", "trade war",
        "oil", "energy supply", "conflict"
    ]):
        return "GEO_FINANCIAL"

    return "NON_FINANCE"

# -----------------------------
# CLARITY VALIDATOR
# -----------------------------

def clarity_checks(text: str, event_type: str, intent: str):
    issues = []
    lower = text.lower()

    # --------------------------------------------------
    # EXPLANATORY + FINANCE POLICY
    # Expect practical impact, not just mechanics
    # --------------------------------------------------
    if intent == "EXPLANATORY" and event_type == "FINANCE_POLICY":
        impact_hits = 0

        # Who is affected
        if any(k in lower for k in [
            "banks", "borrowers", "exporters", "importers",
            "investors", "businesses", "customers", "public"
        ]):
            impact_hits += 1

        # What changes
        if any(k in lower for k in [
            "will change", "new rules", "updated rules",
            "revised", "no longer", "now required"
        ]):
            impact_hits += 1

        # When it applies
        if any(k in lower for k in [
            "effective from", "starting", "from", "on january",
            "from april", "with effect from"
        ]):
            impact_hits += 1

        if impact_hits == 0:
            issues.append("Missing practical impact (who/what/when)")

    # --------------------------------------------------
    # MARKET OPINION
    # Split advice vs prediction
    # --------------------------------------------------
    if intent == "MARKET_OPINION":
        # Explicit advice (hard fail)
        if any(k in lower for k in [
            "you should invest", "recommended to invest",
            "buy now", "sell now", "best investment"
        ]):
            issues.append("Explicit investment advice detected")

        # Forward-looking / predictive language (soft flag)
        if any(k in lower for k in [
            "will likely", "expected to", "set to",
            "poised to", "could lead to"
        ]):
            issues.append("Forward-looking market prediction")

    # --------------------------------------------------
    # DESCRIPTIVE CONTENT
    # Should summarize, not instruct
    # --------------------------------------------------
    if intent == "DESCRIPTIVE":
        if len(text.split()) > 180:
            issues.append("Too long for descriptive summary")

        if any(k in lower for k in [
            "how to participate", "submit bids",
            "competitive bidding", "non-competitive bidding",
            "payment must be made", "settlement date"
        ]):
            issues.append("Too procedural for descriptive content")

    # --------------------------------------------------
    # Universal safety
    # --------------------------------------------------
    if any(k in lower for k in [
        "guaranteed returns", "risk-free profit"
    ]):
        issues.append("Misleading financial claim")

    return issues


# -----------------------------
# INTENT CLASSIFIER
# -----------------------------
def classify_intent(title: str, text: str) -> str:
    combined = f"{title} {text}".lower()

    # Opinionated / positioning language
    if any(k in combined for k in [
        "hot trades", "no reason to own",
        "investors are betting", "positioning",
        "traders expect"
    ]):
        return "MARKET_OPINION"

    # Rules, schemes, mechanisms
    if any(k in combined for k in [
        "regulation", "act", "policy",
        "rules", "scheme", "guidelines"
    ]):
        return "EXPLANATORY"

    return "DESCRIPTIVE"


# -----------------------------
# LOGGER
# -----------------------------

def log_event(data, filename):
    with open(filename, "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

# -----------------------------
# MAIN RUN
# -----------------------------

def run():
    print("🚀 Starting POC run...\n")
    current_time = time.time()
    for source_name, url in RSS_SOURCES.items():
        events = fetch_events(source_name, url)

        for idx, event in enumerate(events, start=1):
            print(f"Processing {source_name} | Event {idx}")

            event_type = classify_event(event.title, event.raw_text)
            intent = classify_intent(event.title, event.raw_text)
            
            explanation = generate_explanation(event,intent)
            clarity_issues = clarity_checks(explanation, event_type, intent)
            record = {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "event_id": event.event_id,
                "source": event.source,
                "event_type": event_type,
                "intent": intent,
                "title": event.title,
                "clarity_issues": clarity_issues,
                "llm_output": explanation
            }

            log_event(record, "logs/events.jsonl")

            print("Clarity issues:", clarity_issues)
            print("-" * 60)
    total_time = time.time() - current_time
    print(f"\n⏱️ Total POC run time: {total_time:.2f} seconds")
    print("\n✅ POC run complete.")

# -----------------------------
# ENTRY POINT
# -----------------------------

if __name__ == "__main__":
    run()
