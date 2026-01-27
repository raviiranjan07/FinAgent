"""
ONNX Export Script for Event Classifier.

Converts trained sklearn LogisticRegression model to ONNX format
for efficient production inference.
"""

import os
import json
import pickle
import argparse
from pathlib import Path

import numpy as np
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import onnxruntime as ort


def load_models(model_dir: str):
    """
    Load trained sklearn models.

    Args:
        model_dir: Directory containing classifier.pkl and label_encoder.pkl

    Returns:
        Tuple of (classifier, label_encoder)
    """
    classifier_path = os.path.join(model_dir, 'classifier.pkl')
    label_encoder_path = os.path.join(model_dir, 'label_encoder.pkl')

    with open(classifier_path, 'rb') as f:
        classifier = pickle.load(f)

    with open(label_encoder_path, 'rb') as f:
        label_encoder = pickle.load(f)

    return classifier, label_encoder


def export_to_onnx(classifier, output_path: str, embedding_dim: int = 384):
    """
    Export sklearn classifier to ONNX format.

    Args:
        classifier: Trained sklearn LogisticRegression
        output_path: Path for output .onnx file
        embedding_dim: Dimension of input embeddings (384 for MiniLM)
    """
    # Define input type
    initial_type = [('input', FloatTensorType([None, embedding_dim]))]

    # Convert to ONNX
    print(f"Converting model to ONNX (input dim: {embedding_dim})...")
    onnx_model = convert_sklearn(
        classifier,
        initial_types=initial_type,
        target_opset=12,
        options={type(classifier): {'zipmap': False}}  # Return arrays, not dicts
    )

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(onnx_model.SerializeToString())

    print(f"Saved ONNX model to {output_path}")
    return onnx_model


def export_label_encoder(label_encoder, output_path: str):
    """
    Export label encoder as JSON for production use.

    Args:
        label_encoder: sklearn LabelEncoder
        output_path: Path for output .json file
    """
    # Create mapping: index -> label
    label_map = {str(i): label for i, label in enumerate(label_encoder.classes_)}

    # Also include reverse mapping for convenience
    export_data = {
        'index_to_label': label_map,
        'label_to_index': {label: str(i) for i, label in enumerate(label_encoder.classes_)},
        'classes': list(label_encoder.classes_)
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(export_data, f, indent=2)

    print(f"Saved label encoder to {output_path}")
    return export_data


def validate_onnx(onnx_path: str, classifier, embedding_dim: int = 384):
    """
    Validate ONNX model produces same output as sklearn model.

    Args:
        onnx_path: Path to ONNX model
        classifier: Original sklearn classifier
        embedding_dim: Input embedding dimension
    """
    print("\nValidating ONNX model...")

    # Create random test input
    np.random.seed(42)
    test_input = np.random.randn(5, embedding_dim).astype(np.float32)

    # sklearn prediction
    sklearn_pred = classifier.predict(test_input)
    sklearn_proba = classifier.predict_proba(test_input)

    # ONNX prediction
    session = ort.InferenceSession(onnx_path)
    input_name = session.get_inputs()[0].name

    onnx_outputs = session.run(None, {input_name: test_input})
    onnx_pred = onnx_outputs[0]  # Labels
    onnx_proba = onnx_outputs[1]  # Probabilities

    # Compare
    labels_match = np.array_equal(sklearn_pred, onnx_pred)
    proba_close = np.allclose(sklearn_proba, onnx_proba, rtol=1e-5, atol=1e-6)

    print(f"Labels match: {labels_match}")
    print(f"Probabilities match (within tolerance): {proba_close}")

    if labels_match and proba_close:
        print("ONNX validation PASSED")
    else:
        print("ONNX validation FAILED")
        print(f"sklearn predictions: {sklearn_pred}")
        print(f"ONNX predictions: {onnx_pred}")

    return labels_match and proba_close


def print_model_info(onnx_path: str, label_map: dict):
    """Print information about the exported model."""
    session = ort.InferenceSession(onnx_path)

    print("\n" + "=" * 60)
    print("EXPORTED MODEL INFO")
    print("=" * 60)

    print("\nInput:")
    for inp in session.get_inputs():
        print(f"  Name: {inp.name}")
        print(f"  Shape: {inp.shape}")
        print(f"  Type: {inp.type}")

    print("\nOutputs:")
    for out in session.get_outputs():
        print(f"  Name: {out.name}")
        print(f"  Shape: {out.shape}")
        print(f"  Type: {out.type}")

    print("\nClasses:")
    for idx, label in sorted(label_map['index_to_label'].items(), key=lambda x: int(x[0])):
        print(f"  {idx}: {label}")

    # File size
    file_size = os.path.getsize(onnx_path) / 1024
    print(f"\nModel size: {file_size:.2f} KB")


def main():
    """Main export function."""
    parser = argparse.ArgumentParser(description='Export classifier to ONNX')
    parser.add_argument(
        '--model-dir', '-m',
        default='ml/models',
        help='Directory containing trained models'
    )
    parser.add_argument(
        '--output-onnx', '-o',
        default='ml/models/event_classifier.onnx',
        help='Output path for ONNX model'
    )
    parser.add_argument(
        '--output-labels', '-l',
        default='ml/models/label_encoder.json',
        help='Output path for label encoder JSON'
    )
    parser.add_argument(
        '--embedding-dim', '-d',
        type=int,
        default=384,
        help='Embedding dimension (384 for MiniLM)'
    )
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip ONNX validation step'
    )

    args = parser.parse_args()

    # Get paths relative to project root
    script_dir = Path(__file__).parent.parent  # FinAgent directory
    model_dir = script_dir / args.model_dir
    onnx_path = script_dir / args.output_onnx
    labels_path = script_dir / args.output_labels

    print("=" * 60)
    print("ONNX EXPORT")
    print("=" * 60)

    # Load models
    print(f"\nLoading models from {model_dir}...")
    classifier, label_encoder = load_models(str(model_dir))
    print(f"Loaded classifier with {len(label_encoder.classes_)} classes")

    # Export to ONNX
    export_to_onnx(classifier, str(onnx_path), args.embedding_dim)

    # Export label encoder
    label_map = export_label_encoder(label_encoder, str(labels_path))

    # Validate
    if not args.skip_validation:
        validation_passed = validate_onnx(
            str(onnx_path),
            classifier,
            args.embedding_dim
        )
        if not validation_passed:
            print("\nWARNING: Validation failed. Check ONNX export.")

    # Print model info
    print_model_info(str(onnx_path), label_map)

    print("\n" + "=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    print(f"\nONNX model: {onnx_path}")
    print(f"Label encoder: {labels_path}")
    print("\nUsage in Python:")
    print("  import onnxruntime as ort")
    print("  session = ort.InferenceSession('event_classifier.onnx')")
    print("  outputs = session.run(None, {'input': embeddings})")
    print("  labels, probabilities = outputs[0], outputs[1]")


if __name__ == "__main__":
    main()
