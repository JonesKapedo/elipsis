"""Email notification service using SendGrid/SES."""

from __future__ import annotations

import os
from typing import Any

# Email service selection
EMAIL_SERVICE = os.getenv("EMAIL_SERVICE", "sendgrid")  # sendgrid or ses

# SendGrid configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "noreply@elipsis.ai")
SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "Elipsis")

# AWS SES configuration
AWS_SES_ACCESS_KEY = os.getenv("AWS_SES_ACCESS_KEY")
AWS_SES_SECRET_KEY = os.getenv("AWS_SES_SECRET_KEY")
AWS_SES_REGION = os.getenv("AWS_SES_REGION", "us-east-1")
AWS_SES_FROM_EMAIL = os.getenv("AWS_SES_FROM_EMAIL", "noreply@elipsis.ai")

# Initialize clients
sendgrid_client = None
ses_client = None

if EMAIL_SERVICE == "sendgrid" and SENDGRID_API_KEY:
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content
        
        sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
    except ImportError:
        print("[elipsis] SendGrid not installed. Run: pip install sendgrid")

elif EMAIL_SERVICE == "ses" and AWS_SES_ACCESS_KEY:
    try:
        import boto3
        
        ses_client = boto3.client(
            'ses',
            aws_access_key_id=AWS_SES_ACCESS_KEY,
            aws_secret_access_key=AWS_SES_SECRET_KEY,
            region_name=AWS_SES_REGION
        )
    except ImportError:
        print("[elipsis] boto3 not installed. Run: pip install boto3")


def is_email_configured() -> bool:
    """Check if email service is configured."""
    return (sendgrid_client is not None) or (ses_client is not None)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None = None
) -> bool:
    """
    Send email using configured service.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text fallback (optional)
    
    Returns:
        True if sent successfully
    """
    if not is_email_configured():
        print(f"[elipsis] Email not configured. Would send to {to_email}: {subject}")
        return False
    
    try:
        if sendgrid_client:
            return await _send_via_sendgrid(to_email, subject, html_content, text_content)
        elif ses_client:
            return await _send_via_ses(to_email, subject, html_content, text_content)
    except Exception as e:
        print(f"[elipsis] Email send failed: {e}")
        return False
    
    return False


async def _send_via_sendgrid(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None
) -> bool:
    """Send email via SendGrid."""
    try:
        from sendgrid.helpers.mail import Mail
        
        message = Mail(
            from_email=(SENDGRID_FROM_EMAIL, SENDGRID_FROM_NAME),
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=text_content or html_content
        )
        
        response = sendgrid_client.send(message)
        return response.status_code in [200, 201, 202]
        
    except Exception as e:
        print(f"[elipsis] SendGrid error: {e}")
        return False


async def _send_via_ses(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None
) -> bool:
    """Send email via AWS SES."""
    try:
        body = {
            'Html': {'Data': html_content, 'Charset': 'UTF-8'}
        }
        if text_content:
            body['Text'] = {'Data': text_content, 'Charset': 'UTF-8'}
        
        response = ses_client.send_email(
            Source=AWS_SES_FROM_EMAIL,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': body
            }
        )
        return True
        
    except Exception as e:
        print(f"[elipsis] SES error: {e}")
        return False


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
