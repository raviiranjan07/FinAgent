"""IntentAdapter - ML-based intent classification using ONNX."""

import os
import json
from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort

from adapters.base import BaseAdapter
from adapters.context import ExecutionContext


class IntentAdapter(BaseAdapter):
    """
    ML-based intent classifier using MiniLM embeddings + Logistic Regression.

    Version 2.0.0 replaces keyword-based matching with ONNX inference.
    Classifies into: EXPLANATORY, DESCRIPTIVE, MARKET_OPINION, BREAKING_NEWS, DATA_RELEASE

    As per documentation Section 4.5.2 IntentAdapter.
    """

    name = "intent_adapter"
    version = "2.0.0"  # ML-based classification
    input_keys = ["event.title", "event.summary", "embedding"]
    output_keys = ["intent", "intent_confidence"]

    # Default threshold (lowered from 0.50 to 0.30 based on testing)
    # Model predictions are accurate even at 30-40% confidence
    DEFAULT_CONFIDENCE_THRESHOLD = 0.30

    def __init__(self):
        """Initialize the ML-based intent adapter."""
        super().__init__()

        # Configuration from environment
        self.confidence_threshold = float(
            os.environ.get("INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD", self.DEFAULT_CONFIDENCE_THRESHOLD)
        )

        # Model paths
        self.model_dir = Path(__file__).parent.parent / "ml" / "models" / "intent"
        self.onnx_path = self.model_dir / "intent_classifier.onnx"
        self.label_encoder_path = self.model_dir / "intent_label_encoder.json"

        # Lazy-loaded components
        self._session: Optional[ort.InferenceSession] = None
        self._label_map: Optional[dict] = None
        self._input_name: Optional[str] = None

    @property
    def session(self) -> ort.InferenceSession:
        """Lazy-load ONNX session."""
        if self._session is None:
            if not self.onnx_path.exists():
                raise FileNotFoundError(
                    f"ONNX model not found at {self.onnx_path}. "
                    "Run 'python -m ml.train_intent && python -m ml.export_intent_onnx' first."
                )
            self._session = ort.InferenceSession(str(self.onnx_path))
            self._input_name = self._session.get_inputs()[0].name
        return self._session

    @property
    def label_map(self) -> dict:
        """Lazy-load label encoder."""
        if self._label_map is None:
            if not self.label_encoder_path.exists():
                raise FileNotFoundError(
                    f"Label encoder not found at {self.label_encoder_path}. "
                    "Run 'python -m ml.export_intent_onnx' first."
                )
            with open(self.label_encoder_path, 'r') as f:
                data = json.load(f)
            self._label_map = data['index_to_label']
        return self._label_map

    def _predict_proba(self, embedding: np.ndarray) -> np.ndarray:
        """
        Run ONNX inference to get class probabilities.

        Args:
            embedding: 384-dimensional embedding vector

        Returns:
            Array of probabilities for each class
        """
        # Ensure correct shape and type
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        embedding = embedding.astype(np.float32)

        # Run inference
        outputs = self.session.run(None, {self._input_name: embedding})

        # outputs[0] = predicted labels, outputs[1] = probabilities
        probabilities = outputs[1][0]  # Get first (only) sample

        return probabilities

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """
        Classify the content intent using ML model.

        Args:
            context: Execution context with event data and optional embedding

        Returns:
            Updated context with intent and intent_confidence
        """
        combined = f"{context.event.title} {context.event.summary or ''}"

        # Get embedding (reuse from context if available)
        embedding = getattr(context, 'embedding', None)
        if embedding is None:
            # Generate embedding if not available
            from utils.embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            embedding = embedding_service.encode(combined)

        # Convert to numpy if needed
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)

        # Run ML inference
        probabilities = self._predict_proba(embedding)

        # Get top prediction
        top_idx = int(np.argmax(probabilities))
        confidence = float(probabilities[top_idx])

        # Apply confidence threshold
        if confidence < self.confidence_threshold:
            # Default to DESCRIPTIVE if confidence is too low
            context.intent = "DESCRIPTIVE"
            context.intent_confidence = confidence
        else:
            context.intent = self.label_map[str(top_idx)]
            context.intent_confidence = confidence

        return context


# =============================================================================
# Legacy Adapter (for fallback/testing) - DEPRECATED v2.0
# =============================================================================
#
# class IntentAdapterKeywordBased(BaseAdapter):
#     """
#     Legacy keyword-based intent classifier.
#
#     Kept for testing and comparison purposes.
#     Use IntentAdapter (ML-based) for production.
#     """
#
#     name = "intent_adapter_keyword"
#     version = "1.0.0"
#     input_keys = ["event.title", "event.summary"]
#     output_keys = ["intent"]
#
#     MARKET_OPINION_KEYWORDS = [
#         "hot trades", "no reason to own", "investors are betting",
#         "positioning", "traders expect"
#     ]
#
#     EXPLANATORY_KEYWORDS = [
#         "regulation", "act", "policy", "rules", "scheme", "guidelines"
#     ]
#
#     def run(self, context: ExecutionContext) -> ExecutionContext:
#         """Classify using keyword matching (legacy)."""
#         combined = f"{context.event.title} {context.event.summary or ''}".lower()
#
#         if any(keyword in combined for keyword in self.MARKET_OPINION_KEYWORDS):
#             context.intent = "MARKET_OPINION"
#             return context
#
#         if any(keyword in combined for keyword in self.EXPLANATORY_KEYWORDS):
#             context.intent = "EXPLANATORY"
#             return context
#
#         context.intent = "DESCRIPTIVE"
#         return context
