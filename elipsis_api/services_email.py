"""Transactional email delivery with Resend, SendGrid, or AWS SES."""

from __future__ import annotations

import asyncio
import os

import httpx

DEFAULT_FROM_EMAIL = "noreply@elipsis.ai"
DEFAULT_FROM_NAME = "Elipsis"
RESEND_ENDPOINT = "https://api.resend.com/emails"


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def email_provider() -> str:
    """Pick an explicit provider, then auto-detect from configured keys."""
    explicit = _env("EMAIL_SERVICE").lower()
    if explicit in {"resend", "sendgrid", "ses"}:
        return explicit
    if _env("RESEND_API_KEY"):
        return "resend"
    if _env("SENDGRID_API_KEY"):
        return "sendgrid"
    if _env("AWS_SES_ACCESS_KEY") and _env("AWS_SES_SECRET_KEY"):
        return "ses"
    return "resend"


def from_email() -> str:
    generic = _env("EMAIL_FROM_EMAIL")
    if generic:
        return generic
    provider = email_provider()
    if provider == "sendgrid":
        return _env("SENDGRID_FROM_EMAIL", DEFAULT_FROM_EMAIL)
    if provider == "ses":
        return _env("AWS_SES_FROM_EMAIL", DEFAULT_FROM_EMAIL)
    return _env("RESEND_FROM_EMAIL", DEFAULT_FROM_EMAIL)


def from_name() -> str:
    generic = _env("EMAIL_FROM_NAME")
    if generic:
        return generic
    if email_provider() == "sendgrid":
        return _env("SENDGRID_FROM_NAME", DEFAULT_FROM_NAME)
    return DEFAULT_FROM_NAME


def from_header() -> str:
    address = from_email()
    name = from_name()
    return f"{name} <{address}>" if name else address


def reply_to() -> str | None:
    return _env("EMAIL_REPLY_TO") or None


def is_email_configured() -> bool:
    """True when a supported provider has enough credentials to send."""
    provider = email_provider()
    if provider == "resend":
        return bool(_env("RESEND_API_KEY"))
    if provider == "sendgrid":
        return bool(_env("SENDGRID_API_KEY"))
    if provider == "ses":
        return bool(_env("AWS_SES_ACCESS_KEY") and _env("AWS_SES_SECRET_KEY"))
    return False


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
) -> bool:
    """Send one transactional email. Never raises into a request handler."""
    to_email = (to_email or "").strip()
    if not to_email or "@" not in to_email:
        print("[elipsis] Email skipped: invalid recipient", flush=True)
        return False
    if not is_email_configured():
        print(f"[elipsis] Email not configured. Would send to {to_email}: {subject}",
              flush=True)
        return False
    try:
        provider = email_provider()
        if provider == "resend":
            return await _send_via_resend(to_email, subject, html_content, text_content)
        if provider == "sendgrid":
            return await _send_via_sendgrid(to_email, subject, html_content, text_content)
        return await _send_via_ses(to_email, subject, html_content, text_content)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] Email send failed: {exc}", flush=True)
        return False


def send_email_sync(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
) -> bool:
    """Synchronous variant for non-async admin and webhook routes."""
    to_email = (to_email or "").strip()
    if not to_email or "@" not in to_email:
        return False
    if not is_email_configured():
        print(f"[elipsis] Email not configured. Would send to {to_email}: {subject}",
              flush=True)
        return False
    try:
        provider = email_provider()
        if provider == "resend":
            return _send_via_resend_sync(to_email, subject, html_content, text_content)
        if provider == "sendgrid":
            return _send_via_sendgrid_sync(to_email, subject, html_content, text_content)
        return _send_via_ses_sync(to_email, subject, html_content, text_content)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] Email send failed: {exc}", flush=True)
        return False


def _resend_payload(to_email: str, subject: str, html_content: str,
                    text_content: str | None) -> dict:
    payload = {
        "from": from_header(),
        "to": [to_email],
        "subject": subject,
        "html": html_content,
        "text": text_content or html_content,
    }
    if reply_to():
        payload["reply_to"] = reply_to()
    return payload


async def _send_via_resend(to_email: str, subject: str, html_content: str,
                           text_content: str | None) -> bool:
    headers = {
        "Authorization": f"Bearer {_env('RESEND_API_KEY')}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            RESEND_ENDPOINT,
            json=_resend_payload(to_email, subject, html_content, text_content),
            headers=headers,
        )
    if response.status_code not in {200, 201, 202}:
        print(f"[elipsis] Resend error {response.status_code}: {response.text[:500]}",
              flush=True)
        return False
    return True


def _send_via_resend_sync(to_email: str, subject: str, html_content: str,
                          text_content: str | None) -> bool:
    headers = {
        "Authorization": f"Bearer {_env('RESEND_API_KEY')}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            RESEND_ENDPOINT,
            json=_resend_payload(to_email, subject, html_content, text_content),
            headers=headers,
        )
    if response.status_code not in {200, 201, 202}:
        print(f"[elipsis] Resend error {response.status_code}: {response.text[:500]}",
              flush=True)
        return False
    return True


def _sendgrid_message(to_email: str, subject: str, html_content: str,
                      text_content: str | None):
    from sendgrid.helpers.mail import Mail

    return Mail(
        from_email=(from_email(), from_name()),
        to_emails=to_email,
        subject=subject,
        html_content=html_content,
        plain_text_content=text_content or html_content,
    )


async def _send_via_sendgrid(to_email: str, subject: str, html_content: str,
                             text_content: str | None) -> bool:
    from sendgrid import SendGridAPIClient

    message = _sendgrid_message(to_email, subject, html_content, text_content)
    client = SendGridAPIClient(_env("SENDGRID_API_KEY"))
    response = await asyncio.to_thread(client.send, message)
    return response.status_code in {200, 201, 202}


def _send_via_sendgrid_sync(to_email: str, subject: str, html_content: str,
                            text_content: str | None) -> bool:
    from sendgrid import SendGridAPIClient

    message = _sendgrid_message(to_email, subject, html_content, text_content)
    response = SendGridAPIClient(_env("SENDGRID_API_KEY")).send(message)
    return response.status_code in {200, 201, 202}


def _ses_body(html_content: str, text_content: str | None) -> dict:
    body = {"Html": {"Data": html_content, "Charset": "UTF-8"}}
    if text_content:
        body["Text"] = {"Data": text_content, "Charset": "UTF-8"}
    return body


def _ses_client():
    import boto3

    return boto3.client(
        "ses",
        aws_access_key_id=_env("AWS_SES_ACCESS_KEY"),
        aws_secret_access_key=_env("AWS_SES_SECRET_KEY"),
        region_name=_env("AWS_SES_REGION", "us-east-1"),
    )


def _send_via_ses_sync(to_email: str, subject: str, html_content: str,
                       text_content: str | None) -> bool:
    _ses_client().send_email(
        Source=from_email(),
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": _ses_body(html_content, text_content),
        },
    )
    return True


async def _send_via_ses(to_email: str, subject: str, html_content: str,
                        text_content: str | None) -> bool:
    return await asyncio.to_thread(
        _send_via_ses_sync, to_email, subject, html_content, text_content)


# Email templates

def render_request_verified_email(
    user_name: str,
    request_title: str,
    request_id: int,
    site_url: str = "https://elipsis.ai"
) -> tuple[str, str]:
    """Render email for request verification notification."""
    subject = f"✅ Your request '{request_title}' has been verified"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(to right, #3B82F6, #06B6D4); padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Elipsis</h1>
        </div>
        
        <div style="padding: 30px; background: #f9fafb;">
            <h2>Great news, {user_name}!</h2>
            
            <p>Your automation service request has been verified and will be published to the marketplace shortly.</p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">{request_title}</h3>
                <p style="color: #6b7280;">Request ID: #{request_id}</p>
            </div>
            
            <p>Qualified bidders will now be able to view and submit proposals for your request.</p>
            
            <p style="margin-top: 30px;">
                <a href="{site_url}/app/requests/{request_id}" 
                   style="background: #3B82F6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    View Your Request
                </a>
            </p>
            
            <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                We'll notify you when bidders submit proposals.
            </p>
        </div>
        
        <div style="padding: 20px; text-align: center; color: #9ca3af; font-size: 12px;">
            <p>© 2026 Elipsis. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Great news, {user_name}!
    
    Your automation service request has been verified: {request_title} (#{request_id})
    
    Qualified bidders can now submit proposals.
    
    View your request: {site_url}/app/requests/{request_id}
    """
    
    return subject, html, text


def render_new_bid_email(
    user_name: str,
    request_title: str,
    bidder_name: str,
    estimated_cost: float,
    timeline: str,
    request_id: int,
    site_url: str = "https://elipsis.ai"
) -> tuple[str, str, str]:
    """Render email for new bid notification."""
    subject = f"💼 New bid received on '{request_title}'"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(to right, #3B82F6, #06B6D4); padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Elipsis</h1>
        </div>
        
        <div style="padding: 30px; background: #f9fafb;">
            <h2>New proposal received, {user_name}!</h2>
            
            <p>A service provider has submitted a bid for your request.</p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">{request_title}</h3>
                
                <div style="margin: 15px 0;">
                    <strong>Bidder:</strong> {bidder_name}<br>
                    <strong>Estimated Cost:</strong> ${estimated_cost:,.2f}<br>
                    <strong>Timeline:</strong> {timeline}
                </div>
            </div>
            
            <p style="margin-top: 30px;">
                <a href="{site_url}/app/requests/{request_id}" 
                   style="background: #3B82F6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    View Proposal
                </a>
            </p>
            
            <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                Review the full proposal and contact the bidder if interested.
            </p>
        </div>
        
        <div style="padding: 20px; text-align: center; color: #9ca3af; font-size: 12px;">
            <p>© 2026 Elipsis. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    New proposal received, {user_name}!
    
    Request: {request_title}
    Bidder: {bidder_name}
    Cost: ${estimated_cost:,.2f}
    Timeline: {timeline}
    
    View proposal: {site_url}/app/requests/{request_id}
    """
    
    return subject, html, text


def render_request_published_email(
    bidder_name: str,
    request_title: str,
    company_name: str,
    budget_range: str,
    request_id: int,
    site_url: str = "https://elipsis.ai"
) -> tuple[str, str, str]:
    """Render email for new published request (bidders)."""
    subject = f"🔔 New marketplace request: {request_title}"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(to right, #3B82F6, #06B6D4); padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Elipsis</h1>
        </div>
        
        <div style="padding: 30px; background: #f9fafb;">
            <h2>New opportunity, {bidder_name}!</h2>
            
            <p>A new automation service request matches your profile.</p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">{request_title}</h3>
                
                <div style="margin: 15px 0;">
                    <strong>Company:</strong> {company_name}<br>
                    <strong>Budget Range:</strong> {budget_range}
                </div>
            </div>
            
            <p style="margin-top: 30px;">
                <a href="{site_url}/app/marketplace" 
                   style="background: #3B82F6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    View in Marketplace
                </a>
            </p>
            
            <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                Submit your proposal before other bidders!
            </p>
        </div>
        
        <div style="padding: 20px; text-align: center; color: #9ca3af; font-size: 12px;">
            <p>© 2026 Elipsis. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    New opportunity, {bidder_name}!
    
    Request: {request_title}
    Company: {company_name}
    Budget: {budget_range}
    
    View in marketplace: {site_url}/app/marketplace
    """
    
    return subject, html, text


def render_welcome_email(
    user_name: str,
    user_type: str,
    site_url: str = "https://elipsis.ai"
) -> tuple[str, str, str]:
    """Render welcome email for new users."""
    subject = "🎉 Welcome to Elipsis!"
    
    next_steps = {
        "client": """
            <li>Complete your company profile</li>
            <li>Browse our marketplace of service providers</li>
            <li>Submit your first automation request</li>
        """,
        "bidder": """
            <li>Set up your bidder shop profile</li>
            <li>Add portfolio projects</li>
            <li>Subscribe to access marketplace requests</li>
            <li>Start submitting proposals</li>
        """
    }
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(to right, #3B82F6, #06B6D4); padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Elipsis</h1>
        </div>
        
        <div style="padding: 30px; background: #f9fafb;">
            <h2>Welcome aboard, {user_name}!</h2>
            
            <p>Thank you for joining Elipsis as a <strong>{user_type}</strong>.</p>
            
            <p>We're excited to help you on your AI automation journey!</p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>Next Steps:</h3>
                <ul>
                    {next_steps.get(user_type, '')}
                </ul>
            </div>
            
            <p style="margin-top: 30px;">
                <a href="{site_url}/app" 
                   style="background: #3B82F6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    Get Started
                </a>
            </p>
        </div>
        
        <div style="padding: 20px; text-align: center; color: #9ca3af; font-size: 12px;">
            <p>© 2026 Elipsis. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Welcome aboard, {user_name}!
    
    Thank you for joining Elipsis as a {user_type}.
    
    Get started: {site_url}/app
    """
    
    return subject, html, text
