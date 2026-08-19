from abc import ABC, abstractmethod
from src.models import SourceAnalysis

class ContentProvider(ABC):
    @abstractmethod
    def analyze(self, prompt: str) -> SourceAnalysis: ...

class LocalProvider(ContentProvider):
    """Test/demo provider. Production model providers implement the same contract."""
    def analyze(self, prompt: str) -> SourceAnalysis:
        raise NotImplementedError("Use the deterministic workflow or configure OpenAI.")
