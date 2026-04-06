"""
Email Service - Production Quality
Handles all email notifications using Resend
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import resend

from app.core.config import settings


class EmailService:
    """
    Email notification service using Resend

    Features:
    - Welcome emails
    - Pipeline notifications
    - Lead alerts
    - Export notifications
    - Usage warnings
    """

    def __init__(self):
        """Initialize email service"""
        resend.api_key = settings.RESEND_API_KEY
        self.from_email = settings.RESEND_FROM_EMAIL
        self.app_name = settings.APP_NAME

    async def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """
        Send welcome email to new user

        Args:
            to_email: User's email
            user_name: User's name

        Returns:
            True if sent successfully
        """
        subject = f"Welcome to {self.app_name}! 🎉"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Welcome to {self.app_name}</h1>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #667eea;">Hi {user_name}! 👋</h2>
                
                <p>Thank you for joining {self.app_name}. We're excited to help you discover and connect with the right biotech leads.</p>
                
                <h3 style="color: #667eea;">🚀 Get Started</h3>
                <ul style="line-height: 2;">
                    <li><strong>Search PubMed:</strong> Find researchers working on your target topics</li>
                    <li><strong>Score Leads:</strong> Automatically rank leads by relevance</li>
                    <li><strong>Enrich Data:</strong> Find emails and company information</li>
                    <li><strong>Export:</strong> Download your leads in multiple formats</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.BACKEND_CORS_ORIGINS[0]}" 
                       style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Start Searching
                    </a>
                </div>
                
                <h3 style="color: #667eea;">💡 Pro Tips</h3>
                <ul style="line-height: 2;">
                    <li>Use specific keywords like "DILI 3D models" for better results</li>
                    <li>Filter by location to find leads near you</li>
                    <li>Set up automated pipelines for daily updates</li>
                </ul>
                
                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;">
                    Need help? Reply to this email or check our <a href="#">documentation</a>.
                </p>
            </div>
        </body>
        </html>
        """
        return await self._send(to_email, subject, html_content)

    async def send_pipeline_completion_email(
        self,
        to_email: str,
        user_name: str,
        pipeline_name: str,
        leads_created: int,
        execution_time: int,
    ) -> bool:
        """
        Send pipeline completion notification

        Args:
            to_email: User's email
            user_name: User's name
            pipeline_name: Pipeline name
            leads_created: Number of leads created
            execution_time: Execution time in seconds

        Returns:
            True if sent successfully
        """
        subject = f"✅ Pipeline '{pipeline_name}' Completed"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #10b981; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                <h2 style="color: white; margin: 0;">✅ Pipeline Completed</h2>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <p>Hi {user_name},</p>
                
                <p>Your pipeline <strong>"{pipeline_name}"</strong> has completed successfully!</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #10b981;">📊 Results</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Leads Created:</strong></td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">{leads_created}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Execution Time:</strong></td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">{execution_time}s</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px;"><strong>Status:</strong></td>
                            <td style="padding: 10px; text-align: right; color: #10b981;"><strong>Success</strong></td>
                        </tr>
                    </table>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.BACKEND_CORS_ORIGINS[0]}/leads" 
                       style="background: #10b981; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Leads
                    </a>
                </div>
                
                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
                    This is an automated notification from {self.app_name}. You can manage your notification preferences in your account settings.
                </p>
            </div>
        </body>
        </html>
        """
        return await self._send(to_email, subject, html_content)

    async def send_pipeline_error_email(
        self,
        to_email: str,
        user_name: str,
        pipeline_name: str,
        errors: List[Dict[str, Any]],
    ) -> bool:
        """
        Send pipeline error notification

        Args:
            to_email: User's email
            user_name: User's name
            pipeline_name: Pipeline name
            errors: List of errors

        Returns:
            True if sent successfully
        """
        subject = f"⚠️ Pipeline '{pipeline_name}' Failed"

        error_list = "".join(
            [
                f"<li><strong>{error.get('query', 'Unknown')}:</strong> {error.get('error', 'Unknown error')}</li>"
                for error in errors[:5]  # Limit to 5 errors
            ]
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #ef4444; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                <h2 style="color: white; margin: 0;">⚠️ Pipeline Failed</h2>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <p>Hi {user_name},</p>
                
                <p>Your pipeline <strong>"{pipeline_name}"</strong> encountered errors during execution.</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #ef4444;">🔍 Errors</h3>
                    <ul style="color: #666;">
                        {error_list}
                    </ul>
                </div>
                
                <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; color: #92400e;">
                        <strong>💡 What to do:</strong><br>
                        • Check your pipeline configuration<br>
                        • Verify API credentials<br>
                        • Review rate limits<br>
                        • Contact support if issue persists
                    </p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.BACKEND_CORS_ORIGINS[0]}/pipelines" 
                       style="background: #ef4444; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Pipeline
                    </a>
                </div>
                
                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
                    This is an automated notification from {self.app_name}.
                </p>
            </div>
        </body>
        </html>
        """
        return await self._send(to_email, subject, html_content)

    async def send_export_ready_email(
        self,
        to_email: str,
        user_name: str,
        file_name: str,
        download_url: str,
        records_count: int,
        expires_in_hours: int = 168,  # 7 days
    ) -> bool:
        """
        Send export ready notification

        Args:
            to_email: User's email
            user_name: User's name
            file_name: Export file name
            download_url: Download URL
            records_count: Number of records
            expires_in_hours: Hours until expiration

        Returns:
            True if sent successfully
        """
        subject = f"📦 Your export is ready"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #3b82f6; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                <h2 style="color: white; margin: 0;">📦 Export Ready</h2>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <p>Hi {user_name},</p>
                
                <p>Your data export is ready for download!</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>File Name:</strong></td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">{file_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Records:</strong></td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">{records_count:,}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px;"><strong>Expires In:</strong></td>
                            <td style="padding: 10px; text-align: right;">{expires_in_hours} hours</td>
                        </tr>
                    </table>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{download_url}" 
                       style="background: #3b82f6; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Download Export
                    </a>
                </div>
                
                <p style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px; color: #92400e;">
                    ⚠️ This link will expire in {expires_in_hours} hours. Download your export before it expires.
                </p>
                
                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
                    This is an automated notification from {self.app_name}.
                </p>
            </div>
        </body>
        </html>
        """
        return await self._send(to_email, subject, html_content)

    async def send_usage_warning_email(
        self,
        to_email: str,
        user_name: str,
        usage_percentage: float,
        usage_type: str = "leads",
        limit: int = 100,
    ) -> bool:
        """
        Send usage warning email

        Args:
            to_email: User's email
            user_name: User's name
            usage_percentage: Percentage of limit used
            usage_type: Type of usage (leads, searches, exports)
            limit: Usage limit

        Returns:
            True if sent successfully
        """
        subject = f"⚠️ {int(usage_percentage)}% of your {usage_type} limit used"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #f59e0b; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                <h2 style="color: white; margin: 0;">⚠️ Usage Warning</h2>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <p>Hi {user_name},</p>
                
                <p>You've used <strong>{int(usage_percentage)}%</strong> of your monthly {usage_type} limit.</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <div style="background: #fee2e2; height: 30px; border-radius: 15px; overflow: hidden;">
                        <div style="background: #ef4444; height: 100%; width: {usage_percentage}%; transition: width 0.3s;"></div>
                    </div>
                    <p style="text-align: center; margin-top: 10px; color: #666;">
                        <strong>{limit - int(limit * usage_percentage / 100)}</strong> {usage_type} remaining this month
                    </p>
                </div>
                
                <div style="background: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; color: #1e40af;">
                        <strong>💡 Upgrade to Pro for:</strong><br>
                        • 10x more {usage_type}<br>
                        • Advanced features<br>
                        • Priority support<br>
                        • No daily limits
                    </p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.BACKEND_CORS_ORIGINS[0]}/upgrade" 
                       style="background: #3b82f6; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Upgrade Now
                    </a>
                </div>
                
                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
                    Your usage resets on the 1st of each month.
                </p>
            </div>
        </body>
        </html>
        """
        return await self._send(to_email, subject, html_content)

    async def send_team_invitation(
        self,
        to_email: str,
        team_name: str,
        inviter: str,
        invite_url: str,
    ) -> bool:
        """Send a team invitation email via Resend."""
        subject = f"You've been invited to join {team_name}"
        html_content = f"""
        <h2>Team Invitation</h2>
        <p><strong>{inviter}</strong> has invited you to join the team
           <strong>{team_name}</strong> on Biotech Lead Generator.</p>
        <p>
          <a href="{invite_url}"
             style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;">
            Accept Invitation
          </a>
        </p>
        <p><small>This link expires in 7 days.</small></p>
        """
        return await self._send(to_email, subject, html_content)

    async def send_daily_digest(
        self,
        to_email: str,
        user_name: str,
        stats: Dict[str, Any],
    ) -> bool:
        """Send a daily digest email with recent lead activity."""
        leads_today = stats.get("leads_today", 0)
        top_leads = stats.get("top_leads", [])
        pipelines_run = stats.get("pipelines_run", 0)
        high_value = stats.get("high_value_count", 0)

        if leads_today == 0 and pipelines_run == 0:
            return True

        top_rows = ""
        for lead in top_leads[:5]:
            score = lead.get("score", 0)
            badge_color = "#16a34a" if score >= 70 else "#d97706" if score >= 50 else "#6b7280"
            top_rows += f"<tr><td style=\"padding:8px;border-bottom:1px solid #eee;\">{lead.get('name','—')}</td><td style=\"padding:8px;border-bottom:1px solid #eee;\">{lead.get('company','—')}</td><td style=\"padding:8px;border-bottom:1px solid #eee;\"><span style=\"background:{badge_color};color:white;padding:2px 8px;border-radius:999px;font-size:12px;\">{score}</span></td><td style=\"padding:8px;border-bottom:1px solid #eee;\">{lead.get('source','—')}</td></tr>"

        table_html = ""
        if top_leads:
            table_html = f"<h3 style=\"color:#667eea;\">🏆 Top New Leads</h3><table style=\"width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;\"><thead><tr style=\"background:#667eea;color:white;\"><th style=\"padding:10px;text-align:left;\">Name</th><th style=\"padding:10px;text-align:left;\">Company</th><th style=\"padding:10px;text-align:left;\">Score</th><th style=\"padding:10px;text-align:left;\">Source</th></tr></thead><tbody>{top_rows}</tbody></table>"

        subject = f"Your daily lead digest — {leads_today} new leads"
        html_content = f"""<!DOCTYPE html><html><body style=\"font-family:Arial,sans-serif;color:#333;max-width:640px;margin:0 auto;padding:20px;\"><div style=\"background:linear-gradient(135deg,#667eea,#764ba2);padding:24px;border-radius:10px 10px 0 0;\"><h1 style=\"color:white;margin:0;font-size:20px;\">📊 Daily Lead Digest</h1><p style=\"color:rgba(255,255,255,0.85);margin:4px 0 0;\">Hi {user_name}</p></div><div style=\"background:#f9f9f9;padding:24px;border-radius:0 0 10px 10px;\"><div style=\"display:flex;gap:16px;margin-bottom:24px;\"><div style=\"flex:1;background:white;padding:16px;border-radius:8px;text-align:center;border:1px solid #eee;\"><div style=\"font-size:28px;font-weight:bold;color:#667eea;\">{leads_today}</div><div style=\"font-size:12px;color:#888;\">New Leads</div></div><div style=\"flex:1;background:white;padding:16px;border-radius:8px;text-align:center;border:1px solid #eee;\"><div style=\"font-size:28px;font-weight:bold;color:#16a34a;\">{high_value}</div><div style=\"font-size:12px;color:#888;\">HIGH Priority</div></div><div style=\"flex:1;background:white;padding:16px;border-radius:8px;text-align:center;border:1px solid #eee;\"><div style=\"font-size:28px;font-weight:bold;color:#d97706;\">{pipelines_run}</div><div style=\"font-size:12px;color:#888;\">Pipelines Run</div></div></div>{table_html}<div style=\"text-align:center;margin-top:24px;\"><a href=\"{settings.FRONTEND_URL}/dashboard\" style=\"background:#667eea;color:white;padding:12px 28px;text-decoration:none;border-radius:6px;\">View All Leads →</a></div><p style=\"font-size:11px;color:#aaa;text-align:center;margin-top:20px;\">You're receiving this because daily digests are enabled. <a href=\"{settings.FRONTEND_URL}/settings\">Unsubscribe</a></p></div></body></html>"""
        return await self._send(to_email, subject, html_content)

    async def send_high_value_lead_alert(
        self,
        to_email: str,
        user_name: str,
        lead_name: str,
        lead_company: str,
        lead_score: int,
        lead_id: str,
        trigger_reason: str,
    ) -> bool:
        """Send an immediate high-value lead alert."""
        subject = f"🎯 High-value lead discovered: {lead_name} (score {lead_score})"
        html_content = f"""<!DOCTYPE html><html><body style=\"font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;padding:20px;\"><div style=\"background:#16a34a;padding:20px;border-radius:10px 10px 0 0;\"><h2 style=\"color:white;margin:0;\">🎯 High-Value Lead Alert</h2></div><div style=\"background:#f0fdf4;padding:24px;border-radius:0 0 10px 10px;border:1px solid #dcfce7;\"><p>Hi {user_name}, a new lead just scored <strong>{lead_score}/100</strong>:</p><table style=\"width:100%;background:white;border-radius:8px;padding:16px;\"><tr><td style=\"color:#888;padding:6px 0;\">Name</td><td style=\"font-weight:bold;\">{lead_name}</td></tr><tr><td style=\"color:#888;padding:6px 0;\">Company</td><td>{lead_company}</td></tr><tr><td style=\"color:#888;padding:6px 0;\">Score</td><td><span style=\"background:#16a34a;color:white;padding:2px 10px;border-radius:999px;\">{lead_score}</span></td></tr><tr><td style=\"color:#888;padding:6px 0;\">Why</td><td style=\"color:#15803d;\">{trigger_reason}</td></tr></table><div style=\"text-align:center;margin-top:20px;\"><a href=\"{settings.FRONTEND_URL}/dashboard/leads/{lead_id}\" style=\"background:#16a34a;color:white;padding:12px 28px;text-decoration:none;border-radius:6px;\">View Lead →</a></div></div></body></html>"""
        return await self._send(to_email, subject, html_content)

    async def _send(self, to_email: str, subject: str, html_content: str) -> bool:
        try:
            resend.Emails.send({"from": self.from_email, "to": [to_email], "subject": subject, "html": html_content})
            return True
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Email send failed: %s", exc)
            return False


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """
    Get singleton EmailService instance

    Usage:
        service = get_email_service()
        await service.send_welcome_email(email, name)
    """
    global _email_service

    if _email_service is None:
        _email_service = EmailService()

    return _email_service


__all__ = [
    "EmailService",
    "get_email_service",
]
