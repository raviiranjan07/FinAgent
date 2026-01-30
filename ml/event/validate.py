"""
Validation Script for Event Classifier.

Validates the ML classifier against historical data from PostgreSQL.
Compares ML predictions with keyword-based labels.
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
import onnxruntime as ort
from sentence_transformers import SentenceTransformer
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score


def clean_text(text: str) -> str:
    """
    Preprocess text for ML inference.

    Matches the preprocessing used during training:
    - Remove HTML tags
    - Lowercase
    - Remove extra whitespace
    - Remove special characters noise

    Args:
        text: Raw text (may contain HTML)

    Returns:
        Cleaned text ready for embedding
    """
    if not text:
        return ""

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Remove HTML entities (&nbsp;, &amp;, etc.)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'&#\d+;', ' ', text)

    # Remove URLs
    text = re.sub(r'http[s]?://\S+', ' ', text)

    # Lowercase
    text = text.lower()

    # Remove extra whitespace (multiple spaces, newlines, tabs)
    text = re.sub(r'\s+', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


class EventClassifierValidator:
    """Validates event classifier against historical data."""

    def __init__(
        self,
        onnx_path: str,
        label_encoder_path: str,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize validator.

        Args:
            onnx_path: Path to ONNX model
            label_encoder_path: Path to label encoder JSON
            embedding_model: SentenceTransformer model name
        """
        # Load ONNX model
        self.session = ort.InferenceSession(onnx_path)
        self.input_name = self.session.get_inputs()[0].name

        # Load label encoder
        with open(label_encoder_path, 'r') as f:
            label_data = json.load(f)
        self.index_to_label = label_data['index_to_label']
        self.classes = label_data['classes']

        # Load embedding model
        print(f"Loading embedding model: {embedding_model}")
        self.encoder = SentenceTransformer(embedding_model)

    def predict(self, texts: List[str]) -> Tuple[List[str], np.ndarray]:
        """
        Predict categories for texts.

        Args:
            texts: List of text strings

        Returns:
            Tuple of (predicted labels, probabilities)
        """
        # Encode texts
        embeddings = self.encoder.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        ).astype(np.float32)

        # Run inference
        outputs = self.session.run(None, {self.input_name: embeddings})
        pred_indices = outputs[0]
        probabilities = outputs[1]

        # Convert indices to labels
        labels = [self.index_to_label[str(idx)] for idx in pred_indices]

        return labels, probabilities

    def predict_with_confidence(
        self,
        texts: List[str],
        primary_threshold: float = 0.55,
        secondary_threshold: float = 0.40
    ) -> List[Dict]:
        """
        Predict with confidence scores and secondary labels.

        Args:
            texts: List of text strings
            primary_threshold: Threshold for primary label
            secondary_threshold: Threshold for secondary label

        Returns:
            List of prediction dictionaries
        """
        labels, probabilities = self.predict(texts)

        results = []
        for i, (label, proba) in enumerate(zip(labels, probabilities)):
            # Sort probabilities descending
            sorted_indices = np.argsort(proba)[::-1]

            primary_idx = sorted_indices[0]
            primary_conf = proba[primary_idx]
            primary_label = self.index_to_label[str(primary_idx)]

            # Check confidence threshold
            if primary_conf < primary_threshold:
                primary_label = "NON_FINANCE"

            result = {
                'text': texts[i],
                'primary_label': primary_label,
                'primary_confidence': float(primary_conf),
                'secondary_label': None,
                'secondary_confidence': None
            }

            # Secondary label
            if primary_conf >= primary_threshold:
                secondary_idx = sorted_indices[1]
                secondary_conf = proba[secondary_idx]
                if secondary_conf >= secondary_threshold:
                    result['secondary_label'] = self.index_to_label[str(secondary_idx)]
                    result['secondary_confidence'] = float(secondary_conf)

            results.append(result)

        return results

    def validate_against_csv(self, csv_path: str) -> Dict:
        """
        Validate against labeled CSV data.

        Args:
            csv_path: Path to CSV with 'text' and 'label' columns

        Returns:
            Validation metrics dictionary
        """
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} samples from {csv_path}")

        # Predict
        predictions, probabilities = self.predict(df['text'].tolist())

        # Calculate metrics
        true_labels = df['label'].tolist()
        accuracy = accuracy_score(true_labels, predictions)

        # Classification report
        report = classification_report(
            true_labels,
            predictions,
            output_dict=True,
            zero_division=0
        )

        # Confusion matrix
        cm = confusion_matrix(true_labels, predictions, labels=self.classes)

        # Find disagreements
        disagreements = []
        for i, (true, pred) in enumerate(zip(true_labels, predictions)):
            if true != pred:
                disagreements.append({
                    'text': df['text'].iloc[i],
                    'true_label': true,
                    'predicted_label': pred,
                    'confidence': float(max(probabilities[i]))
                })

        return {
            'total_samples': len(df),
            'accuracy': accuracy,
            'classification_report': report,
            'confusion_matrix': cm.tolist(),
            'classes': self.classes,
            'disagreements': disagreements,
            'disagreement_count': len(disagreements)
        }


def validate_against_database(validator: EventClassifierValidator, limit: int = 500):
    """
    Validate against PostgreSQL database.

    Args:
        validator: EventClassifierValidator instance
        limit: Maximum samples to validate

    Returns:
        Validation metrics or None if database not available
    """
    try:
        # Try to import database modules
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from database.connection import get_db_session
        from database.repository import EventRepository, OutputRepository

        print(f"\nFetching up to {limit} events from database...")

        with get_db_session() as db:
            output_repo = OutputRepository(db)

            # Get outputs with event_type
            samples = []
            for event_type in validator.classes:
                if event_type in ['NON_FINANCE', 'SKIP']:
                    continue

                outputs = output_repo.get_by_event_type(event_type, limit=limit // 6)
                for output in outputs:
                    if output.event:
                        # Combine title + summary and preprocess
                        raw_text = f"{output.event.title} {output.event.summary or ''}"
                        text = clean_text(raw_text)

                        # Skip empty texts after cleaning
                        if not text:
                            continue

                        samples.append({
                            'text': text,
                            'label': event_type
                        })

            if not samples:
                print("No samples found in database")
                return None

            print(f"Retrieved {len(samples)} samples from database")

            # Convert to DataFrame
            df = pd.DataFrame(samples)

            # Save for reference
            output_path = Path(__file__).parent / 'data' / 'db_validation_samples.csv'
            df.to_csv(output_path, index=False)
            print(f"Saved samples to {output_path}")

            # Validate
            return validator.validate_against_csv(str(output_path))

    except ImportError as e:
        print(f"Database modules not available: {e}")
        print("Skipping database validation")
        return None
    except Exception as e:
        print(f"Database validation error: {e}")
        return None


def print_validation_report(metrics: Dict):
    """Print formatted validation report."""
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    print(f"\nTotal samples: {metrics['total_samples']}")
    print(f"Overall accuracy: {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")

    print("\n--- Per-Category Metrics ---")
    report = metrics['classification_report']
    for category in metrics['classes']:
        if category in report:
            cat_metrics = report[category]
            print(f"\n{category}:")
            print(f"  Precision: {cat_metrics['precision']:.4f}")
            print(f"  Recall:    {cat_metrics['recall']:.4f}")
            print(f"  F1-score:  {cat_metrics['f1-score']:.4f}")
            print(f"  Support:   {cat_metrics['support']}")

    print(f"\n--- Disagreements ({metrics['disagreement_count']} total) ---")
    for d in metrics['disagreements'][:10]:  # Show first 10
        print(f"\nText: {d['text'][:80]}...")
        print(f"  True: {d['true_label']} | Predicted: {d['predicted_label']} (conf: {d['confidence']:.2f})")

    if metrics['disagreement_count'] > 10:
        print(f"\n... and {metrics['disagreement_count'] - 10} more disagreements")


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description='Validate event classifier')
    parser.add_argument(
        '--onnx', '-o',
        default='ml/models/event_classifier.onnx',
        help='Path to ONNX model'
    )
    parser.add_argument(
        '--labels', '-l',
        default='ml/models/label_encoder.json',
        help='Path to label encoder JSON'
    )
    parser.add_argument(
        '--data', '-d',
        default=None,
        help='Path to validation CSV (optional, uses synthetic data if not provided)'
    )
    parser.add_argument(
        '--use-database',
        action='store_true',
        help='Validate against PostgreSQL database'
    )
    parser.add_argument(
        '--db-limit',
        type=int,
        default=500,
        help='Max samples from database'
    )
    parser.add_argument(
        '--save-disagreements',
        default=None,
        help='Path to save disagreements CSV'
    )

    args = parser.parse_args()

    # Get paths
    script_dir = Path(__file__).parent.parent  # FinAgent directory
    onnx_path = script_dir / args.onnx
    labels_path = script_dir / args.labels

    print("=" * 60)
    print("EVENT CLASSIFIER VALIDATION")
    print("=" * 60)

    # Initialize validator
    print(f"\nLoading model from {onnx_path}")
    validator = EventClassifierValidator(
        str(onnx_path),
        str(labels_path)
    )

    # Validate
    if args.use_database:
        print("\nValidating against database...")
        metrics = validate_against_database(validator, args.db_limit)
    elif args.data:
        data_path = script_dir / args.data
        print(f"\nValidating against {data_path}")
        metrics = validator.validate_against_csv(str(data_path))
    else:
        # Default to synthetic data
        data_path = script_dir / 'ml/data/synthetic_train.csv'
        if data_path.exists():
            print(f"\nValidating against synthetic data: {data_path}")
            metrics = validator.validate_against_csv(str(data_path))
        else:
            print("No validation data found. Generate synthetic data first:")
            print("  python -m ml.data.generator")
            return

    if metrics:
        print_validation_report(metrics)

        # Save disagreements
        if args.save_disagreements and metrics['disagreements']:
            disagreements_df = pd.DataFrame(metrics['disagreements'])
            save_path = script_dir / args.save_disagreements
            disagreements_df.to_csv(save_path, index=False)
            print(f"\nSaved disagreements to {save_path}")


if __name__ == "__main__":
    main()
