"""EventTypeAdapter - ML-based event classification using ONNX."""

import os
import re
import json
from pathlib import Path
from typing import Optional, Tuple, List

import numpy as np
import onnxruntime as ort

from adapters.base import BaseAdapter
from adapters.context import ExecutionContext
from ml.event.validate import clean_text


class EventTypeAdapter(BaseAdapter):
    """
    ML-based event classifier using MiniLM embeddings + Logistic Regression.

    Version 2.0.0 replaces keyword-based matching with ONNX inference.
    Skip patterns remain rule-based for fast filtering of administrative content.
    """

    name = "event_type_adapter"
    version = "2.0.0"  # ML-based classification
    input_keys = ["event.title", "event.summary", "embedding"]
    output_keys = ["event_type", "event_type_confidence", "secondary_event_type", "secondary_event_type_confidence"]

    # Patterns that indicate content should be skipped (rule-based, fast)
    SKIP_PATTERNS = [
        r"appeal\s+no\.\s*\d+",           # "Appeal No. 6674 of 2026"
        r"appeal\s+nos?\.\s*\d+",         # "Appeal Nos. 6670 & 6671"
        r"filed\s+by\s+[A-Z][a-z]+",      # "filed by Murali krishna"
        r"order\s+in\s+the\s+matter\s+of", # SEBI enforcement orders
        # Q&A / Personal Advice column patterns
        r"^(my|i'm|i am|we're|we are)\s+",  # "My neighbor...", "I'm inheriting..."
        r"\?\s*$",                        # Ends with question mark (advice columns)
        r"(should|can|will|do|does)\s+(i|you|we)\s+", # "Should I...", "Can you..."
    ]

    # Default thresholds
    DEFAULT_CONFIDENCE_THRESHOLD = 0.55
    DEFAULT_SECONDARY_THRESHOLD = 0.40

    def __init__(self):
        """Initialize the ML-based event type adapter."""
        super().__init__()

        # Configuration from environment
        self.confidence_threshold = float(
            os.environ.get("EVENT_CLASSIFIER_CONFIDENCE_THRESHOLD", self.DEFAULT_CONFIDENCE_THRESHOLD)
        )
        self.secondary_threshold = float(
            os.environ.get("EVENT_CLASSIFIER_SECONDARY_THRESHOLD", self.DEFAULT_SECONDARY_THRESHOLD)
        )

        # Model paths
        self.model_dir = Path(__file__).parent.parent / "ml" / "models"
        self.onnx_path = self.model_dir / "event_classifier.onnx"
        self.label_encoder_path = self.model_dir / "label_encoder.json"

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
                    "Run 'python -m ml.train && python -m ml.export_onnx' first."
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
                    "Run 'python -m ml.export_onnx' first."
                )
            with open(self.label_encoder_path, 'r') as f:
                data = json.load(f)
            self._label_map = data['index_to_label']
        return self._label_map

    def _is_skip(self, text: str) -> bool:
        """
        Check if text matches any skip pattern.

        Args:
            text: Combined title + summary text

        Returns:
            True if content should be skipped
        """
        for pattern in self.SKIP_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

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
        Classify the event type using ML model.

        Args:
            context: Execution context with event data and optional embedding

        Returns:
            Updated context with event_type, confidence, and optional secondary_event_type
        """
        raw_text = f"{context.event.title} {context.event.summary or ''}"
        combined = clean_text(raw_text)

        # 1. Check skip patterns first (rule-based, fast)
        if self._is_skip(raw_text):  # Use raw text for skip patterns (case-insensitive anyway)
            context.event_type = "SKIP"
            context.event_type_confidence = 1.0
            context.secondary_event_type = None
            context.secondary_event_type_confidence = None
            return context

        # 2. Get embedding (reuse from context if available)
        embedding = getattr(context, 'embedding', None)
        if embedding is None:
            # Generate embedding if not available
            # This should rarely happen as EmbeddingAdapter runs first
            from utils.embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            embedding = embedding_service.encode(combined)

        # Convert to numpy if needed
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)

        # 3. Run ML inference
        probabilities = self._predict_proba(embedding)

        # 4. Get sorted indices (descending by probability)
        sorted_indices = np.argsort(probabilities)[::-1]

        primary_idx = sorted_indices[0]
        primary_conf = float(probabilities[primary_idx])
        primary_label = self.label_map[str(primary_idx)]

        # 5. Apply confidence threshold
        if primary_conf < self.confidence_threshold:
            context.event_type = "NON_FINANCE"
            context.event_type_confidence = primary_conf
            context.secondary_event_type = None
            context.secondary_event_type_confidence = None
        else:
            context.event_type = primary_label
            context.event_type_confidence = primary_conf

            # 6. Check for secondary label
            secondary_idx = sorted_indices[1]
            secondary_conf = float(probabilities[secondary_idx])

            if secondary_conf >= self.secondary_threshold:
                context.secondary_event_type = self.label_map[str(secondary_idx)]
                context.secondary_event_type_confidence = secondary_conf
            else:
                context.secondary_event_type = None
                context.secondary_event_type_confidence = None

        return context


# =============================================================================
# Legacy Adapter (for fallback/testing) - DEPRECATED v2.0
# =============================================================================
#
# class EventTypeAdapterKeywordBased(BaseAdapter):
#     """
#     Legacy keyword-based event classifier.
#
#     Kept for testing and comparison purposes.
#     Use EventTypeAdapter (ML-based) for production.
#     """
#
#     name = "event_type_adapter_keyword"
#     version = "1.6.0"
#     input_keys = ["event.title", "event.summary"]
#     output_keys = ["event_type"]
#
#     SKIP_PATTERNS = [
#         r"appeal\s+no\.\s*\d+",
#         r"appeal\s+nos?\.\s*\d+",
#         r"filed\s+by\s+[A-Z][a-z]+",
#         r"order\s+in\s+the\s+matter\s+of",
#         r"^(my|i'm|i am|we're|we are)\s+",
#         r"\?\s*$",
#         r"(should|can|will|do|does)\s+(i|you|we)\s+",
#     ]
#
#     KEYWORDS = {
#         "FINANCE_POLICY": [
#             "rbi", "sebi", "regulation", "policy", "act", "scheme",
#             "federal reserve", "enforcement action", "ecb", "central bank"
#         ],
#         "DIGITAL_ASSETS": [
#             "crypto", "cryptocurrency", "bitcoin", "ethereum", "blockchain",
#             "etf", "exchange traded fund", "staking", "defi", "decentralized finance",
#             "nft", "digital asset", "web3", "altcoin", "token", "mining",
#             "wallet", "binance", "coinbase", "solana", "cardano", "ripple", "xrp"
#         ],
#         "MARKET_INFRASTRUCTURE": [
#             "stock exchange", "commodity exchange", "nse", "bse", "nyse", "nasdaq",
#             "bond", "treasury", "bill", "auction", "mou", "clearing"
#         ],
#         "MARKET_MOVEMENT": [
#             "stocks", "shares", "markets", "selloff", "sink", "rally",
#             "risk sentiment", "trades"
#         ],
#         "MACRO_ECONOMIC": [
#             "inflation", "gdp", "interest rate", "liquidity", "money supply",
#             "fomc", "federal open market", "discount rate", "federal funds",
#             "monetary policy", "rate decision", "basis points"
#         ],
#         "GEO_FINANCIAL": [
#             "tariff", "sanction", "trade war", "oil", "energy supply", "conflict",
#             "yen", "dollar", "euro", "currency", "forex", "foreign exchange",
#             "intervention", "intervene", "exchange rate", "depreciation",
#             "appreciation", "weaken", "strengthen", "currency market"
#         ]
#     }
#
#     def run(self, context: ExecutionContext) -> ExecutionContext:
#         """Classify using keyword matching (legacy)."""
#         combined = f"{context.event.title} {context.event.summary or ''}".lower()
#
#         for pattern in self.SKIP_PATTERNS:
#             if re.search(pattern, combined, re.IGNORECASE):
#                 context.event_type = "SKIP"
#                 return context
#
#         for event_type, keywords in self.KEYWORDS.items():
#             if any(keyword in combined for keyword in keywords):
#                 context.event_type = event_type
#                 return context
#
#         context.event_type = "NON_FINANCE"
#         return context
