import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


@dataclass(frozen=True)
class PipelineSettings:
    # Image Quality Validation Thresholds
    BLUR_THRESHOLD: float = float(os.getenv("LM_BLUR_THRESHOLD", "40.0"))
    DEBLUR_THRESHOLD: float = float(os.getenv("LM_DEBLUR_THRESHOLD", "80.0"))
    MIN_IMAGE_WIDTH: int = int(os.getenv("LM_MIN_IMAGE_WIDTH", "300"))
    MIN_IMAGE_HEIGHT: int = int(os.getenv("LM_MIN_IMAGE_HEIGHT", "200"))
    MIN_BRIGHTNESS: float = float(os.getenv("LM_MIN_BRIGHTNESS", "30.0"))
    MAX_BRIGHTNESS: float = float(os.getenv("LM_MAX_BRIGHTNESS", "245.0"))
    MIN_CONTRAST: float = float(os.getenv("LM_MIN_CONTRAST", "20.0"))
    MAX_NOISE_STD: float = float(os.getenv("LM_MAX_NOISE_STD", "35.0"))
    MAX_SKEW_ANGLE: float = float(os.getenv("LM_MAX_SKEW_ANGLE", "45.0"))

    # OCR Confidence & Retries
    CONFIDENCE_HIGH: float = float(os.getenv("LM_CONFIDENCE_HIGH", "0.70"))
    CONFIDENCE_MEDIUM: float = float(os.getenv("LM_CONFIDENCE_MEDIUM", "0.45"))
    MAX_OCR_RETRIES: int = int(os.getenv("LM_MAX_OCR_RETRIES", "5"))

    # Compliance Scoring
    COMPLIANCE_THRESHOLD: float = float(os.getenv("LM_COMPLIANCE_THRESHOLD", "80.0"))

    # Gemini AI Vision & Extraction Settings (Loaded from environment variables)
    GCP_API_KEY: str = os.getenv("GCP_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GCP_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    GEMINI_FALLBACK_MODEL: str = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash")
    GEMINI_TIMEOUT: float = float(os.getenv("LM_GEMINI_TIMEOUT", "30.0"))
    GEMINI_ENABLED: bool = os.getenv("LM_GEMINI_ENABLED", "true").lower() in ("true", "1", "yes")


settings = PipelineSettings()

