"""Embedding service for semantic similarity detection."""

import time
import numpy as np
from typing import List, Optional
from config.settings import SIMILARITY_MODEL


class EmbeddingService:
    """
    Singleton embedding service with lazy model loading.

    Uses sentence-transformers for generating text embeddings.
    Model is loaded only once on first use.
    """

    _instance: Optional['EmbeddingService'] = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            print(f"Loading embedding model: {SIMILARITY_MODEL}...")
            start_time = time.time()
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(SIMILARITY_MODEL)
            load_time = time.time() - start_time
            print(f"Embedding model loaded in {load_time:.2f}s")
        return self._model

    def encode(self, text: str) -> List[float]:
        """
        Encode text into embedding vector.

        Args:
            text: Text to encode

        Returns:
            List of floats (384-dim for MiniLM)
        """
        model = self._load_model()
        start_time = time.time()
        embedding = model.encode(text, convert_to_numpy=True)
        encode_time = time.time() - start_time
        print(f"    [Embedding] Encoded text in {encode_time:.3f}s")
        return embedding.tolist()

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Encode multiple texts into embedding vectors.

        Args:
            texts: List of texts to encode

        Returns:
            List of embedding vectors
        """
        model = self._load_model()
        start_time = time.time()
        embeddings = model.encode(texts, convert_to_numpy=True)
        encode_time = time.time() - start_time
        print(f"    [Embedding] Batch encoded {len(texts)} texts in {encode_time:.3f}s")
        return [emb.tolist() for emb in embeddings]

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Similarity score between 0 and 1
        """
        a = np.array(vec1)
        b = np.array(vec2)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))
