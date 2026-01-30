"""
Training Pipeline for Event Classification.

Trains a Logistic Regression classifier on MiniLM embeddings.
"""

import os
import pickle
import argparse
from pathlib import Path
from typing import Tuple, Dict, Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sentence_transformers import SentenceTransformer


class EventClassifierTrainer:
    """Trains event classification model."""

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        max_iter: int = 1000,
        class_weight: str = "balanced",
        random_state: int = 42
    ):
        """
        Initialize trainer.

        Args:
            embedding_model: SentenceTransformer model name
            max_iter: Maximum iterations for LogisticRegression
            class_weight: Class weight strategy
            random_state: Random seed for reproducibility
        """
        self.embedding_model_name = embedding_model
        self.max_iter = max_iter
        self.class_weight = class_weight
        self.random_state = random_state

        # Will be initialized during training
        self.encoder = None
        self.classifier = None
        self.label_encoder = None

    def load_data(self, data_path: str) -> pd.DataFrame:
        """
        Load training data from CSV.

        Args:
            data_path: Path to CSV file

        Returns:
            DataFrame with text and label columns
        """
        df = pd.read_csv(data_path)

        if 'text' not in df.columns or 'label' not in df.columns:
            raise ValueError("CSV must have 'text' and 'label' columns")

        print(f"Loaded {len(df)} samples from {data_path}")
        print(f"Label distribution:\n{df['label'].value_counts()}")

        return df

    def encode_texts(self, texts: list) -> np.ndarray:
        """
        Encode texts using SentenceTransformer.

        Args:
            texts: List of text strings

        Returns:
            numpy array of embeddings (N x 384)
        """
        if self.encoder is None:
            print(f"Loading embedding model: {self.embedding_model_name}")
            self.encoder = SentenceTransformer(self.embedding_model_name)

        print(f"Encoding {len(texts)} texts...")
        embeddings = self.encoder.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        print(f"Embedding shape: {embeddings.shape}")
        return embeddings

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train the classifier.

        Args:
            X: Embeddings array
            y: Labels array (encoded)
            test_size: Fraction of data for validation

        Returns:
            Dictionary with training metrics
        """
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=test_size,
            random_state=self.random_state,
            stratify=y
        )

        print(f"\nTraining set: {len(X_train)} samples")
        print(f"Validation set: {len(X_val)} samples")

        # Train classifier
        print("\nTraining Logistic Regression classifier...")
        # Note: multi_class parameter removed in sklearn 1.5+
        # 'lbfgs' solver automatically uses multinomial for multi-class
        self.classifier = LogisticRegression(
            max_iter=self.max_iter,
            solver='lbfgs',
            class_weight=self.class_weight,
            random_state=self.random_state,
            n_jobs=-1
        )

        self.classifier.fit(X_train, y_train)

        # Evaluate
        train_acc = accuracy_score(y_train, self.classifier.predict(X_train))
        val_acc = accuracy_score(y_val, self.classifier.predict(X_val))

        print(f"\nTraining accuracy: {train_acc:.4f}")
        print(f"Validation accuracy: {val_acc:.4f}")

        # Detailed report
        y_pred = self.classifier.predict(X_val)
        report = classification_report(
            y_val, y_pred,
            target_names=self.label_encoder.classes_,
            output_dict=True
        )

        print("\nClassification Report:")
        print(classification_report(
            y_val, y_pred,
            target_names=self.label_encoder.classes_
        ))

        # Confusion matrix
        cm = confusion_matrix(y_val, y_pred)

        return {
            'train_accuracy': train_acc,
            'val_accuracy': val_acc,
            'classification_report': report,
            'confusion_matrix': cm,
            'classes': list(self.label_encoder.classes_)
        }

    def fit(self, data_path: str, test_size: float = 0.2) -> Dict[str, Any]:
        """
        Full training pipeline: load data, encode, train.

        Args:
            data_path: Path to training CSV
            test_size: Validation split size

        Returns:
            Training metrics
        """
        # Load data
        df = self.load_data(data_path)

        # Encode labels
        self.label_encoder = LabelEncoder()  # convert text labels (categories) into numeric labels
        y = self.label_encoder.fit_transform(df['label'])

        print(f"\nClasses: {list(self.label_encoder.classes_)}")

        # Encode texts
        X = self.encode_texts(df['text'].tolist())

        # Train
        metrics = self.train(X, y, test_size)

        return metrics

    def save(self, output_dir: str):
        """
        Save trained model and label encoder.

        Args:
            output_dir: Directory to save models
        """
        os.makedirs(output_dir, exist_ok=True)

        # Save classifier
        classifier_path = os.path.join(output_dir, 'classifier.pkl')
        with open(classifier_path, 'wb') as f:
            pickle.dump(self.classifier, f)
        print(f"Saved classifier to {classifier_path}")

        # Save label encoder
        label_encoder_path = os.path.join(output_dir, 'label_encoder.pkl')
        with open(label_encoder_path, 'wb') as f:
            pickle.dump(self.label_encoder, f)
        print(f"Saved label encoder to {label_encoder_path}")

    def load(self, model_dir: str):
        """
        Load trained model and label encoder.

        Args:
            model_dir: Directory containing models
        """
        # Load classifier
        classifier_path = os.path.join(model_dir, 'classifier.pkl')
        with open(classifier_path, 'rb') as f:
            self.classifier = pickle.load(f)

        # Load label encoder
        label_encoder_path = os.path.join(model_dir, 'label_encoder.pkl')
        with open(label_encoder_path, 'rb') as f:
            self.label_encoder = pickle.load(f)

        print(f"Loaded model from {model_dir}")

    def predict(self, texts: list) -> Tuple[list, np.ndarray]:
        """
        Predict categories for texts.

        Args:
            texts: List of text strings

        Returns:
            Tuple of (predicted labels, probabilities)
        """
        if self.classifier is None:
            raise ValueError("Model not trained or loaded")

        # Encode
        embeddings = self.encode_texts(texts)

        # Predict
        y_pred = self.classifier.predict(embeddings)
        y_proba = self.classifier.predict_proba(embeddings)

        # Decode labels
        labels = self.label_encoder.inverse_transform(y_pred)

        return labels, y_proba


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Train event classifier')
    parser.add_argument(
        '--data', '-d',
        default='ml/data/synthetic_train.csv',
        help='Path to training data CSV'
    )
    parser.add_argument(
        '--output', '-o',
        default='ml/models',
        help='Output directory for models'
    )
    parser.add_argument(
        '--embedding-model', '-e',
        default='all-MiniLM-L6-v2',
        help='SentenceTransformer model name'
    )
    parser.add_argument(
        '--max-iter', '-m',
        type=int,
        default=1000,
        help='Max iterations for LogisticRegression'
    )
    parser.add_argument(
        '--test-size', '-t',
        type=float,
        default=0.2,
        help='Validation split size'
    )
    parser.add_argument(
        '--seed', '-s',
        type=int,
        default=42,
        help='Random seed'
    )

    args = parser.parse_args()

    # Get paths relative to project root
    script_dir = Path(__file__).parent.parent  # FinAgent directory
    data_path = script_dir / args.data
    output_dir = script_dir / args.output

    # Initialize trainer
    trainer = EventClassifierTrainer(
        embedding_model=args.embedding_model,
        max_iter=args.max_iter,
        random_state=args.seed
    )

    # Train
    print("=" * 60)
    print("EVENT CLASSIFIER TRAINING")
    print("=" * 60)

    metrics = trainer.fit(str(data_path), test_size=args.test_size)

    # Save
    trainer.save(str(output_dir))

    # Summary
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Training accuracy: {metrics['train_accuracy']:.4f}")
    print(f"Validation accuracy: {metrics['val_accuracy']:.4f}")
    print(f"\nModels saved to: {output_dir}")
    print("\nNext step: Run 'python -m ml.export_onnx' to export to ONNX format")


if __name__ == "__main__":
    main()
