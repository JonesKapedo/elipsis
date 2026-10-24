import asyncio

from elipsis_api import services_email, services_email_events


class _Response:
    status_code = 202
    text = ""


class _AsyncClient:
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        self.__class__.calls.append((url, json, headers))
        return _Response()


def test_resend_transport_posts_expected_payload(monkeypatch):
    monkeypatch.setenv("EMAIL_SERVICE", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("EMAIL_FROM_NAME", "Elipsis Test")
    monkeypatch.setenv("EMAIL_REPLY_TO", "support@example.com")
    monkeypatch.setattr(services_email.httpx, "AsyncClient", _AsyncClient)
    _AsyncClient.calls = []

    sent = asyncio.run(services_email.send_email(
        "person@example.com", "Subject", "<p>Hello</p>", "Hello"))

    assert sent is True
    url, payload, headers = _AsyncClient.calls[0]
    assert url == services_email.RESEND_ENDPOINT
    assert payload["from"] == "Elipsis Test <noreply@example.com>"
    assert payload["to"] == ["person@example.com"]
    assert payload["reply_to"] == "support@example.com"
    assert payload["subject"] == "Subject"
    assert headers["Authorization"] == "Bearer re_test"


def test_email_unconfigured_does_not_send(monkeypatch):
    monkeypatch.setenv("EMAIL_SERVICE", "resend")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    monkeypatch.delenv("AWS_SES_ACCESS_KEY", raising=False)

    assert services_email.is_email_configured() is False
    assert asyncio.run(services_email.send_email(
        "person@example.com", "Subject", "<p>Hello</p>")) is False


def test_event_html_is_escaped_and_links_use_public_url(monkeypatch):
    monkeypatch.setenv("ELIPSIS_PUBLIC_URL", "https://example.com")

    subject, body, text = services_email_events.render_event(
        "conversation_message", name="Ada", request_title="<script>alert(1)</script>",
        sender_name="Bob", message="<b>unsafe</b>",
        url="/marketplace/conversations/4")

    assert subject == "New message about <script>alert(1)</script>"
    assert "<script>" not in body
    assert "&lt;script&gt;" in body
    assert "https://example.com/marketplace/conversations/4" in body
    assert "https://example.com/marketplace/conversations/4" in text


def test_event_preferences_skip_optional_email():
    class Prefs:
        notify_email = 0

    class DB:
        def get(self, model, key):
            return Prefs()

    assert services_email_events._allows(DB(), 1, "conversation_message") is False
    assert services_email_events._allows(DB(), 1, "payment_receipt") is True
