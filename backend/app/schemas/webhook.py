"""
Webhook Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, validator

from app.models.webhook import WebhookEventType

# ============================================================================
# WEBHOOK SCHEMAS
# ============================================================================


class WebhookBase(BaseModel):
    """Base webhook schema"""

    name: str = Field(..., min_length=1, max_length=255, description="Webhook name")
    url: HttpUrl = Field(..., description="Webhook URL endpoint")
    events: List[str] = Field(..., description="Event types to listen for")

    @validator("events")
    def validate_events(cls, v):
        """Validate event types"""
        valid_events = [e.value for e in WebhookEventType]
        for event in v:
            if event not in valid_events:
                raise ValueError(
                    f"Invalid event type: {event}. Valid types: {valid_events}"
                )
        return v


class WebhookCreate(WebhookBase):
    """Create webhook request"""

    pass


class WebhookUpdate(BaseModel):
    """Update webhook request"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[HttpUrl] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @validator("events")
    def validate_events(cls, v):
        """Validate event types"""
        if v is None:
            return v
        valid_events = [e.value for e in WebhookEventType]
        for event in v:
            if event not in valid_events:
                raise ValueError(f"Invalid event type: {event}")
        return v


class WebhookResponse(WebhookBase):
    """Webhook response"""

    id: UUID
    user_id: UUID
    secret_key: str = Field(..., description="Secret key for signature verification")
    is_active: bool

    # Statistics
    last_triggered_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    success_count: int
    failure_count: int

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookTestResponse(BaseModel):
    """Webhook test response"""

    success: bool
    message: str


# ============================================================================
# WEBHOOK EVENT SCHEMAS
# ============================================================================


class WebhookEventResponse(BaseModel):
    """Webhook event response"""

    id: UUID
    webhook_id: UUID
    event_type: WebhookEventType
    payload: Dict[str, Any]

    # Delivery
    attempts: int
    delivered_at: Optional[datetime] = None
    response_status_code: Optional[int] = None
    response_body: Optional[str] = None

    # Timestamp
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# WEBHOOK PAYLOAD SCHEMAS
# ============================================================================


class PipelineCompletedPayload(BaseModel):
    """Pipeline completed event payload"""

    pipeline_id: str
    pipeline_name: str
    results: Dict[str, Any]


class PipelineFailedPayload(BaseModel):
    """Pipeline failed event payload"""

    pipeline_id: str
    pipeline_name: str
    error: str


class LeadCreatedPayload(BaseModel):
    """Lead created event payload"""

    lead_id: str
    lead: Dict[str, Any]


class LeadEnrichedPayload(BaseModel):
    """Lead enriched event payload"""

    lead_id: str
    enrichment_data: Dict[str, Any]


class ExportReadyPayload(BaseModel):
    """Export ready event payload"""

    export_id: str
    file_url: str
    file_name: str
    records_count: int
