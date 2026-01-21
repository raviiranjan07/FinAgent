"""Base adapter contract for the adapter pipeline."""

from abc import ABC, abstractmethod
from typing import List
from adapters.context import ExecutionContext


class BaseAdapter(ABC):
    """
    Abstract base class for all adapters.

    Every adapter must expose:
    - name: Unique adapter identifier
    - version: Semantic version
    - input_keys: Context keys this adapter reads
    - output_keys: Context keys this adapter writes
    - run(context): Execute adapter logic

    Contract Rules (from documentation Section 4.4):
    - Adapters never control execution flow
    - Adapters only read from input_keys and write to output_keys
    - Adapters must be stateless (no side effects between runs)
    """

    name: str = "base_adapter"
    version: str = "1.0.0"
    input_keys: List[str] = []
    output_keys: List[str] = []

    @abstractmethod
    def run(self, context: ExecutionContext) -> ExecutionContext:
        """
        Execute adapter logic on the context.

        Args:
            context: The shared ExecutionContext object

        Returns:
            Updated ExecutionContext with adapter's output_keys populated
        """
        pass

    def __repr__(self) -> str:
        return f"{self.name} v{self.version}"
