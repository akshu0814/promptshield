import logging
import os
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from transformers import pipeline as hf_pipeline
except ImportError:
    hf_pipeline = None

MODEL_NAME = os.getenv(
    "ML_MODEL_NAME",
    "protectai/deberta-v3-base-prompt-injection-v2"
)

ML_CONFIDENCE_THRESHOLD = float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.85"))
ML_ENABLED = os.getenv("ML_ENABLED", "true").lower() != "false"


@dataclass
class MLMatch:
    category: str
    severity: str
    confidence: float
    rule_id: str = "ML001"
    name: str = "ML Classifier Detection"
    description: str = "Detected by HuggingFace ML classifier"


class MLClassifier:
    def __init__(self):
        self._pipeline = None
        self._loaded = False
        self._failed = False

    def load(self) -> bool:
        """
        Load the HuggingFace model. Returns True on success, False on failure.
        Failure is non-fatal — system falls back to regex-only mode.
        """
        if not ML_ENABLED:
            logger.info("ML classifier disabled via ML_ENABLED env var")
            return False

        try:
            if hf_pipeline is None:
                raise ImportError("transformers not installed")
            logger.info("Loading ML model: %s", MODEL_NAME)
            self._pipeline = hf_pipeline(
                "text-classification",
                model=MODEL_NAME,
                truncation=True,
                max_length=512,
            )
            self._loaded = True
            logger.info("ML classifier loaded successfully")
            return True
        except Exception as e:
            self._failed = True
            logger.warning(
                "ML classifier failed to load — running regex-only mode: %s", e
            )
            return False

    def classify(self, text: str) -> Optional[MLMatch]:
        """
        Run text through the ML model.
        Returns MLMatch if injection detected above threshold, else None.
        Fail-open: any error returns None.
        """
        if not self._loaded or self._pipeline is None:
            return None

        try:
            result = self._pipeline(text)[0]
            label = result["label"].upper()
            confidence = float(result["score"])

            logger.debug("ML result: label=%s confidence=%.3f", label, confidence)

            # Model labels: INJECTION or SAFE (varies by model version)
            is_injection = label in ("INJECTION", "LABEL_1", "1")

            if is_injection and confidence >= ML_CONFIDENCE_THRESHOLD:
                return MLMatch(
                    category="prompt_injection",
                    severity=_confidence_to_severity(confidence),
                    confidence=confidence,
                )
        except Exception as e:
            logger.warning("ML classification error (fail-open): %s", e)

        return None

    @property
    def is_loaded(self) -> bool:
        return self._loaded


def _confidence_to_severity(confidence: float) -> str:
    if confidence >= 0.97:
        return "critical"
    elif confidence >= 0.92:
        return "high"
    elif confidence >= 0.85:
        return "medium"
    return "low"


# Module-level singleton
_classifier_instance: Optional[MLClassifier] = None


def get_classifier() -> MLClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = MLClassifier()
        _classifier_instance.load()
    return _classifier_instance


def reset_classifier() -> None:
    """For testing — force a fresh classifier on next get_classifier() call."""
    global _classifier_instance
    _classifier_instance = None
