from typing import Optional
from pydantic import BaseModel

class Analysis(BaseModel):
    asset: str = "OTHER"
    summary: str = ""
    impact: str = "neutral"
    impact_strength: int = 0
    time_horizon: str = "medium_term"
    why_it_matters: str = ""
    source_quality: str = "unknown"
    original_text: str = ""
    message_id: str = ""
    timestamp: str = ""

class AnalysisResponse(BaseModel):
    success: bool
    analysis: Optional[Analysis] = None
    error: Optional[str] = None