# POC Automation Project

## High-Level Automation Flow (POC)

```
RSS
   ↓
Event Normalization
   ↓
Event Type Classification        ← (finance / geo / non-finance)
   ↓
Intent Classification            ← (explanatory / opinion / descriptive)
   ↓
LLM Explanation (Ollama)
   ↓
Intent-aware Clarity Rules
   ↓
Structured Logs (JSONL)
   ↓
Human Review (manual)
```

## Project Structure

```
poc/
├── feeds/
│   └── rss_sources.yaml
├── fetcher/
│   └── rss_fetcher.py
├── normalizer/
│   └── event_schema.py
├── llm/
│   ├── prompt.txt
│   └── generator.py
├── validators/
│   └── clarity_rules.py
├── logs/
│   ├── events.jsonl
│   └── evaluations.jsonl
├── run_poc.py
└── requirements.txt
```