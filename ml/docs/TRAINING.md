# Training Workflow Documentation

This document describes the complete training workflow for the event classifier.

---

## Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Generate Data  │ ──► │  Train Model    │ ──► │  Export ONNX    │
│  (synthetic)    │     │  (sklearn)      │     │  (production)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                      │                       │
         ▼                      ▼                       ▼
   synthetic_train.csv    classifier.pkl      event_classifier.onnx
                          label_encoder.pkl   label_encoder.json
```

---

## Step 1: Generate Synthetic Data

### Command

```bash
python -m ml.data.generator
```

### What it does

1. Loads templates from `ml/data/templates.py`
2. Generates samples by random placeholder substitution
3. Applies variation (case, punctuation)
4. Outputs to `ml/data/synthetic_train.csv`

### Output format

```csv
text,label
"RBI announces new lending guidelines for NBFCs",FINANCE_POLICY
"Bitcoin rallies as ETF approval news breaks",DIGITAL_ASSETS
...
```

### Target samples per category

| Category | Target Samples |
|----------|----------------|
| FINANCE_POLICY | 800 |
| DIGITAL_ASSETS | 800 |
| MARKET_INFRASTRUCTURE | 700 |
| MARKET_MOVEMENT | 700 |
| MACRO_ECONOMIC | 800 |
| GEO_FINANCIAL | 700 |
| SKIP | 500 |
| NON_FINANCE | 500 |
| **Total** | **~5500** |

### Configuration

```python
# In ml/data/generator.py
SAMPLES_PER_CATEGORY = {
    "FINANCE_POLICY": 800,
    "DIGITAL_ASSETS": 800,
    "MARKET_INFRASTRUCTURE": 700,
    "MARKET_MOVEMENT": 700,
    "MACRO_ECONOMIC": 800,
    "GEO_FINANCIAL": 700,
    "SKIP": 500,
    "NON_FINANCE": 500,
}
```

---

## Step 2: Train the Model

### Command

```bash
python -m ml.train
```

### What it does

1. Loads synthetic training data from CSV
2. Encodes text using MiniLM (`all-MiniLM-L6-v2`)
3. Trains Logistic Regression classifier
4. Evaluates on train/test split
5. Saves model and label encoder

### Training Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `max_iter` | 1000 | Maximum iterations for convergence |
| `multi_class` | multinomial | Multi-class strategy |
| `solver` | lbfgs | Optimization algorithm |
| `class_weight` | balanced | Handle imbalanced classes |
| `test_size` | 0.2 | 20% held out for validation |
| `random_state` | 42 | Reproducibility |

### Code snippet

```python
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sentence_transformers import SentenceTransformer

# Load data
df = pd.read_csv("ml/data/synthetic_train.csv")

# Encode text
encoder = SentenceTransformer("all-MiniLM-L6-v2")
X = encoder.encode(df["text"].tolist(), show_progress_bar=True)

# Encode labels
le = LabelEncoder()
y = le.fit_transform(df["label"])

# Train
clf = LogisticRegression(
    max_iter=1000,
    multi_class="multinomial",
    solver="lbfgs",
    class_weight="balanced",
    random_state=42
)
clf.fit(X_train, y_train)

# Save
pickle.dump(clf, open("ml/models/classifier.pkl", "wb"))
pickle.dump(le, open("ml/models/label_encoder.pkl", "wb"))
```

### Output files

| File | Description |
|------|-------------|
| `ml/models/classifier.pkl` | Trained sklearn LogisticRegression |
| `ml/models/label_encoder.pkl` | sklearn LabelEncoder |

### Expected metrics

| Metric | Target |
|--------|--------|
| Training accuracy | > 95% |
| Validation accuracy | > 90% |
| Per-class F1 | > 0.85 |

---

## Step 3: Export to ONNX

### Command

```bash
python -m ml.export_onnx
```

### What it does

1. Loads trained sklearn model
2. Converts to ONNX format using `skl2onnx`
3. Exports label mapping to JSON
4. Validates ONNX model output

### Code snippet

```python
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

# Load model
clf = pickle.load(open("ml/models/classifier.pkl", "rb"))
le = pickle.load(open("ml/models/label_encoder.pkl", "rb"))

# Define input shape (384-dim embedding)
initial_type = [("input", FloatTensorType([None, 384]))]

# Convert to ONNX
onnx_model = convert_sklearn(
    clf,
    initial_types=initial_type,
    target_opset=12
)

# Save ONNX model
with open("ml/models/event_classifier.onnx", "wb") as f:
    f.write(onnx_model.SerializeToString())

# Save label mapping
label_map = {i: label for i, label in enumerate(le.classes_)}
with open("ml/models/label_encoder.json", "w") as f:
    json.dump(label_map, f, indent=2)
```

### Output files

| File | Description |
|------|-------------|
| `ml/models/event_classifier.onnx` | ONNX model for production |
| `ml/models/label_encoder.json` | Label index to name mapping |

### label_encoder.json format

```json
{
  "0": "DIGITAL_ASSETS",
  "1": "FINANCE_POLICY",
  "2": "GEO_FINANCIAL",
  "3": "MACRO_ECONOMIC",
  "4": "MARKET_INFRASTRUCTURE",
  "5": "MARKET_MOVEMENT",
  "6": "NON_FINANCE",
  "7": "SKIP"
}
```

---

## Step 4: Validate Against Historical Data

### Command

```bash
python -m ml.validate
```

### What it does

1. Connects to PostgreSQL database
2. Queries recent events with existing labels
3. Runs ML predictions on each event
4. Compares ML vs keyword-based labels
5. Generates confusion matrix and metrics

### Output

```
=== Validation Results ===

Total events: 500
Agreement with keyword baseline: 87.4%

Per-category accuracy:
  FINANCE_POLICY:       91.2%
  DIGITAL_ASSETS:       94.5%
  MARKET_INFRASTRUCTURE: 85.3%
  MARKET_MOVEMENT:      82.1%
  MACRO_ECONOMIC:       89.7%
  GEO_FINANCIAL:        88.4%

Confusion Matrix:
[confusion matrix output]

Disagreements saved to: ml/validation_disagreements.csv
```

### Interpreting results

- **Agreement > 85%:** Model learned keyword patterns well
- **Agreement < 80%:** May need more/better training data
- **Low per-category accuracy:** Add more templates for that category

---

## Retraining

### When to retrain

1. New category added
2. Significant accuracy drop observed
3. New keywords/patterns emerge
4. Category definitions change

### Retraining process

```bash
# 1. Update templates if needed
# Edit ml/data/templates.py

# 2. Regenerate training data
python -m ml.data.generator

# 3. Retrain model
python -m ml.train

# 4. Re-export ONNX
python -m ml.export_onnx

# 5. Validate
python -m ml.validate

# 6. Deploy (model files auto-loaded on restart)
```

---

## Troubleshooting

### Low training accuracy

- **Cause:** Templates too similar across categories
- **Fix:** Add more diverse templates, ensure no overlap

### Model not converging

- **Cause:** `max_iter` too low
- **Fix:** Increase `max_iter` to 2000+

### Poor validation accuracy

- **Cause:** Synthetic data doesn't match real data distribution
- **Fix:** Add more realistic templates, review real articles for patterns

### ONNX export fails

- **Cause:** Incompatible sklearn version
- **Fix:** Update `skl2onnx` to latest version

---

## Configuration Reference

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ML_MODELS_DIR` | `ml/models` | Directory for model files |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `CONFIDENCE_THRESHOLD` | `0.55` | Primary label threshold |
| `SECONDARY_THRESHOLD` | `0.40` | Secondary label threshold |

### File paths

| File | Purpose |
|------|---------|
| `ml/data/synthetic_train.csv` | Training data |
| `ml/models/classifier.pkl` | Sklearn model |
| `ml/models/label_encoder.pkl` | Label encoder |
| `ml/models/event_classifier.onnx` | Production model |
| `ml/models/label_encoder.json` | Label mapping |
