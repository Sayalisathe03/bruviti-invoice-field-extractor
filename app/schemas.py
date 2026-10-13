"""Pydantic schemas for request validation and response serialization."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ConfidenceScores(BaseModel):
    """Confidence scores for each of the eight extracted business fields."""

    vendor: float = Field(..., ge=0.0, le=1.0, description="Confidence in vendor identification")
    invoice_number: float = Field(..., ge=0.0, le=1.0, description="Confidence in invoice number extraction")
    invoice_date: float = Field(..., ge=0.0, le=1.0, description="Confidence in invoice date extraction")
    due_date: float = Field(..., ge=0.0, le=1.0, description="Confidence in due date extraction")
    currency: float = Field(..., ge=0.0, le=1.0, description="Confidence in currency identification")
    subtotal: float = Field(..., ge=0.0, le=1.0, description="Confidence in subtotal extraction")
    tax: float = Field(..., ge=0.0, le=1.0, description="Confidence in tax extraction")
    total: float = Field(..., ge=0.0, le=1.0, description="Confidence in total extraction")

    model_config = ConfigDict(extra="forbid")


class ExtractionResponse(BaseModel):
    """Contract response model for invoice extraction."""

    vendor: str = Field(..., description="Canonical vendor name or 'unknown'")
    invoice_number: Optional[str] = Field(None, description="Preserved invoice identifier or null")
    invoice_date: Optional[str] = Field(None, description="Normalized ISO date YYYY-MM-DD or null")
    due_date: Optional[str] = Field(None, description="Normalized ISO date YYYY-MM-DD or null")
    currency: Optional[str] = Field(None, description="ISO 4217 currency code or null")
    subtotal: Optional[float] = Field(None, description="Normalized monetary subtotal or null")
    tax: Optional[float] = Field(None, description="Normalized monetary tax or null")
    total: Optional[float] = Field(None, description="Normalized monetary total or null")
    confidence: ConfidenceScores = Field(..., description="Per-field confidence scores")
    warnings: List[str] = Field(default_factory=list, description="Human-readable processing warnings")

    model_config = ConfigDict(extra="forbid")


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = "ok"
