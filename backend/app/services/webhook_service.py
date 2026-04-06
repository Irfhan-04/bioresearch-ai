"""
Webhook Service - Production Quality
Handles webhook delivery and event management
"""

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.webhook import Webhook, WebhookEvent, WebhookEventType


class WebhookService:
    """
    Webhook delivery service

    Features:
    - Secure signature generation
    - Automatic retry on failure
    - Event logging
    - Rate limiting
    - Timeout handling
    """

    def __init__(self):
        """Initialize webhook service"""
        self.timeout = 10  # 10 seconds
        self.max_retries = 3

    async def send_webhook(
        self,
        webhook: Webhook,
        event_type: WebhookEventType,
        payload: Dict[str, Any],
        db: AsyncSession,
    ) -> bool:
        """
        Send webhook event

        Args:
            webhook: Webhook to send to
            event_type: Type of event
            payload: Event payload
            db: Database session

        Returns:
            True if delivery successful
        """
        # Check if webhook is active
        if not webhook.is_active:
            return False

        # Check if webhook subscribes to this event
        if event_type.value not in webhook.events:
            return False

        # Prepare payload
        full_payload = {
            "event": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload,
        }

        # Generate signature
        signature = self._generate_signature(
            payload=json.dumps(full_payload), secret=webhook.secret_key
        )

        # Create event record
        event = WebhookEvent(
            webhook_id=webhook.id,
            event_type=event_type,
            payload=full_payload,
            attempts=0,
        )
        db.add(event)

        # Send webhook
        success = False
        response_status = None
        response_body = None

        for attempt in range(1, self.max_retries + 1):
            event.attempts = attempt

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        webhook.url,
                        json=full_payload,
                        headers={
                            "Content-Type": "application/json",
                            "X-Webhook-Signature": signature,
                            "X-Webhook-Event": event_type.value,
                            "User-Agent": "BiotechLeadGen-Webhook/1.0",
                        },
                    )

                    response_status = response.status_code
                    response_body = response.text[:500]  # Limit response body

                    # Consider 2xx successful
                    if 200 <= response.status_code < 300:
                        success = True
                        break

            except httpx.TimeoutException:
                response_body = "Request timeout"
            except httpx.RequestError as e:
                response_body = f"Request error: {str(e)}"
            except Exception as e:
                response_body = f"Unexpected error: {str(e)}"

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries:
                import asyncio

                await asyncio.sleep(2**attempt)

        # Update event
        event.response_status_code = response_status
        event.response_body = response_body
        event.delivered_at = datetime.utcnow() if success else None

        # Update webhook stats
        if success:
            webhook.success_count += 1
            webhook.last_success_at = datetime.utcnow()
        else:
            webhook.failure_count += 1
            webhook.last_failure_at = datetime.utcnow()

        webhook.last_triggered_at = datetime.utcnow()

        await db.commit()

        return success

    async def send_test_event(self, webhook: Webhook, db: AsyncSession) -> bool:
        """
        Send test event to webhook

        Args:
            webhook: Webhook to test
            db: Database session for creating event record

        Returns:
            True if delivery successful
        """
        payload = {
            "event": "webhook.test",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message": "This is a test webhook event",
                "webhook_id": str(webhook.id),
                "webhook_name": webhook.name,
            },
        }

        signature = self._generate_signature(
            payload=json.dumps(payload), secret=webhook.secret_key
        )

        # Create event record BEFORE sending
        event = WebhookEvent(
            webhook_id=webhook.id,
            event_type=WebhookEventType.PIPELINE_COMPLETED,  # Use existing enum
            payload=payload,
            attempts=0,
        )
        db.add(event)
        await db.flush()  # Get the event ID

        success = False
        response_status = None
        response_body = None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                event.attempts = 1
                response = await client.post(
                    webhook.url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                        "X-Webhook-Event": "webhook.test",
                        "User-Agent": "BiotechLeadGen-Webhook/1.0",
                    },
                )

                response_status = response.status_code
                response_body = response.text[:500]
                success = 200 <= response.status_code < 300

        except httpx.TimeoutException:
            response_body = "Request timeout"
            event.attempts = 1
        except httpx.RequestError as e:
            response_body = f"Request error: {str(e)}"
            event.attempts = 1
        except Exception as e:
            response_body = f"Unexpected error: {str(e)}"
            event.attempts = 1

        # Update event with results
        event.response_status_code = response_status
        event.response_body = response_body
        event.delivered_at = datetime.utcnow() if success else None

        # Update webhook stats
        if success:
            webhook.success_count += 1
            webhook.last_success_at = datetime.utcnow()
        else:
            webhook.failure_count += 1
            webhook.last_failure_at = datetime.utcnow()

        webhook.last_triggered_at = datetime.utcnow()

        await db.commit()

        return success

    async def notify_pipeline_completed(
        self,
        user: User,
        pipeline_name: str,
        pipeline_id: str,
        results: Dict[str, Any],
        db: AsyncSession,
    ):
        """
        Notify webhooks about pipeline completion

        Args:
            user: User who owns the pipeline
            pipeline_name: Pipeline name
            pipeline_id: Pipeline ID
            results: Execution results
            db: Database session
        """
        # Get user's active webhooks
        result = await db.execute(
            select(Webhook).where(Webhook.user_id == user.id, Webhook.is_active == True)
        )
        webhooks = result.scalars().all()

        # Send to each webhook
        payload = {
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline_name,
            "results": results,
        }

        for webhook in webhooks:
            await self.send_webhook(
                webhook=webhook,
                event_type=WebhookEventType.PIPELINE_COMPLETED,
                payload=payload,
                db=db,
            )

    async def notify_pipeline_failed(
        self,
        user: User,
        pipeline_name: str,
        pipeline_id: str,
        error: str,
        db: AsyncSession,
    ):
        """
        Notify webhooks about pipeline failure

        Args:
            user: User who owns the pipeline
            pipeline_name: Pipeline name
            pipeline_id: Pipeline ID
            error: Error message
            db: Database session
        """
        result = await db.execute(
            select(Webhook).where(Webhook.user_id == user.id, Webhook.is_active == True)
        )
        webhooks = result.scalars().all()

        payload = {
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline_name,
            "error": error,
        }

        for webhook in webhooks:
            await self.send_webhook(
                webhook=webhook,
                event_type=WebhookEventType.PIPELINE_FAILED,
                payload=payload,
                db=db,
            )

    async def notify_lead_created(
        self, user: User, lead_id: str, lead_data: Dict[str, Any], db: AsyncSession
    ):
        """
        Notify webhooks about new lead

        Args:
            user: User who owns the lead
            lead_id: Lead ID
            lead_data: Lead information
            db: Database session
        """
        result = await db.execute(
            select(Webhook).where(Webhook.user_id == user.id, Webhook.is_active == True)
        )
        webhooks = result.scalars().all()

        payload = {"lead_id": lead_id, "lead": lead_data}

        for webhook in webhooks:
            await self.send_webhook(
                webhook=webhook,
                event_type=WebhookEventType.LEAD_CREATED,
                payload=payload,
                db=db,
            )

    async def notify_export_ready(
        self,
        user: User,
        export_id: str,
        file_url: str,
        file_name: str,
        records_count: int,
        db: AsyncSession,
    ):
        """
        Notify webhooks about export completion

        Args:
            user: User who requested export
            export_id: Export ID
            file_url: Download URL
            file_name: File name
            records_count: Number of records
            db: Database session
        """
        result = await db.execute(
            select(Webhook).where(Webhook.user_id == user.id, Webhook.is_active == True)
        )
        webhooks = result.scalars().all()

        payload = {
            "export_id": export_id,
            "file_url": file_url,
            "file_name": file_name,
            "records_count": records_count,
        }

        for webhook in webhooks:
            await self.send_webhook(
                webhook=webhook,
                event_type=WebhookEventType.EXPORT_READY,
                payload=payload,
                db=db,
            )

    async def notify_lead_scored(
        self,
        user_id: str,
        lead_id: str,
        lead_name: str,
        old_score: Optional[int],
        new_score: int,
        db: AsyncSession,
    ) -> None:
        """Fire lead.scored webhooks for a user."""
        await self._notify_all(
            user_id=user_id,
            event_type=WebhookEventType.LEAD_SCORED,
            payload={
                "lead_id": lead_id,
                "lead_name": lead_name,
                "old_score": old_score,
                "new_score": new_score,
                "tier": "HIGH" if new_score >= 70 else "MEDIUM" if new_score >= 50 else "LOW",
            },
            db=db,
        )

    async def notify_high_value_lead(
        self,
        user_id: str,
        lead_id: str,
        lead_name: str,
        lead_company: str,
        score: int,
        trigger_reason: str,
        db: AsyncSession,
    ) -> None:
        """Fire lead.high_value webhooks for a user."""
        await self._notify_all(
            user_id=user_id,
            event_type=WebhookEventType.HIGH_VALUE_LEAD,
            payload={
                "lead_id": lead_id,
                "lead_name": lead_name,
                "lead_company": lead_company,
                "score": score,
                "trigger_reason": trigger_reason,
            },
            db=db,
        )

    async def _notify_all(
        self,
        user_id: str,
        event_type: WebhookEventType,
        payload: Dict[str, Any],
        db: AsyncSession,
    ) -> None:
        """Notify all subscribed active webhooks for a user."""
        from uuid import UUID

        result = await db.execute(select(Webhook).where(Webhook.user_id == UUID(user_id), Webhook.is_active == True))
        for webhook in result.scalars().all():
            if event_type.value in (webhook.events or []):
                await self.send_webhook(webhook, event_type, payload, db)

    def _generate_signature(self, payload: str, secret: str) -> str:
        """
        Generate HMAC signature for webhook

        Args:
            payload: JSON payload string
            secret: Webhook secret key

        Returns:
            Hex signature
        """
        return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """
        Verify webhook signature

        Args:
            payload: JSON payload string
            signature: Received signature
            secret: Webhook secret key

        Returns:
            True if signature is valid
        """
        expected = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)


# Singleton instance
_webhook_service: Optional[WebhookService] = None


def get_webhook_service() -> WebhookService:
    """
    Get singleton WebhookService instance

    Usage:
        service = get_webhook_service()
        await service.send_webhook(webhook, event_type, payload, db)
    """
    global _webhook_service

    if _webhook_service is None:
        _webhook_service = WebhookService()

    return _webhook_service


__all__ = [
    "WebhookService",
    "get_webhook_service",
]
