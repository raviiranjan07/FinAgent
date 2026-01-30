# Event Classifier - ML Module

## Overview

This module provides an ML-based event classifier to replace the keyword-based `EventTypeAdapter`. It uses **MiniLM embeddings** + **Logistic Regression** exported to **ONNX** format for efficient inference.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Event Classification                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Input: Article (title + summary)                              │
│                    │                                             │
│                    ▼                                             │
│   ┌────────────────────────────────┐                            │
│   │     Skip Pattern Check         │ ──Yes──► SKIP              │
│   │     (Rule-based regex)         │                            │
│   └────────────────────────────────┘                            │
│                    │ No                                          │
│                    ▼                                             │
│   ┌────────────────────────────────┐                            │
│   │     MiniLM Encoder             │                            │
│   │     (all-MiniLM-L6-v2)         │                            │
│   │     Output: 384-dim vector     │                            │
│   └────────────────────────────────┘                            │
│                    │                                             │
│                    ▼                                             │
│   ┌────────────────────────────────┐                            │
│   │     ONNX Classifier            │                            │
│   │     (Logistic Regression)      │                            │
│   │     Output: probabilities      │                            │
│   └────────────────────────────────┘                            │
│                    │                                             │
│                    ▼                                             │
│   ┌────────────────────────────────┐                            │
│   │     Confidence Threshold       │                            │
│   │     Primary: 0.55              │                            │
│   │     Secondary: 0.40            │                            │
│   └────────────────────────────────┘                            │
│                    │                                             │
│                    ▼                                             │
│   Output: event_type + secondary_event_type (optional)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Categories

| Category | Description |
|----------|-------------|
| FINANCE_POLICY | Regulatory announcements, central bank policies |
| DIGITAL_ASSETS | Crypto, blockchain, NFTs, DeFi |
| MARKET_INFRASTRUCTURE | Exchanges, bonds, treasuries |
| MARKET_MOVEMENT | Stock/market movements, sentiment |
| MACRO_ECONOMIC | Inflation, GDP, interest rates |
| GEO_FINANCIAL | Tariffs, sanctions, forex, currency |
| NON_FINANCE | Valid news but not financial (fallback) |
| SKIP | Administrative, legal, personal advice |

See [docs/CATEGORIES.md](docs/CATEGORIES.md) for detailed definitions.

## Quick Start

### 1. Generate Synthetic Training Data

```bash
python -m ml.data.generator
```

Output: `ml/data/synthetic_train.csv`

### 2. Train the Model

```bash
python -m ml.train
```

Output:
- `ml/models/classifier.pkl`
- `ml/models/label_encoder.pkl`

### 3. Export to ONNX

```bash
python -m ml.export_onnx
```

Output:
- `ml/models/event_classifier.onnx`
- `ml/models/label_encoder.json`

### 4. Validate Against Historical Data

```bash
python -m ml.validate
```

## Directory Structure

```
ml/
├── README.md                 # This file
├── __init__.py
├── train.py                  # Training pipeline
├── export_onnx.py            # ONNX export script
├── validate.py               # Validation against PostgreSQL
├── data/
│   ├── __init__.py
│   ├── templates.py          # Template definitions
│   ├── generator.py          # Synthetic data generator
│   ├── skip_examples.py      # SKIP category examples
│   └── synthetic_train.csv   # Generated training data
├── models/
│   ├── classifier.pkl        # Trained sklearn model
│   ├── label_encoder.pkl     # Label encoder
│   ├── event_classifier.onnx # ONNX exported model
│   └── label_encoder.json    # Label mapping for ONNX
└── docs/
    ├── CATEGORIES.md         # Category definitions
    ├── TEMPLATES.md          # Template syntax docs
    └── TRAINING.md           # Training workflow docs
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `confidence_threshold` | 0.55 | Minimum confidence for primary label |
| `secondary_threshold` | 0.40 | Minimum confidence for secondary label |
| `max_iter` | 1000 | Logistic regression max iterations |
| `class_weight` | balanced | Handle imbalanced classes |

## Integration

The trained model integrates with `adapters/event_type.py`:

```python
from ml.models import load_classifier

class EventTypeAdapter(BaseAdapter):
    version = "2.0.0"  # ML-based

    def __init__(self):
        self.session = ort.InferenceSession("ml/models/event_classifier.onnx")
        # ...
```

## Documentation

- [CATEGORIES.md](docs/CATEGORIES.md) - Detailed category definitions
- [TEMPLATES.md](docs/TEMPLATES.md) - Template syntax for data generation
- [TRAINING.md](docs/TRAINING.md) - Training workflow and parameters
