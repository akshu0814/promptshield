import os
import logging
import httpx

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    "low": ":white_circle:",
    "medium": ":yellow_circle:",
    "high": ":orange_circle:",
    "critical": ":red_circle:",
}


async def send_slack_alert(response) -> None:
    """Send a Slack notification for a blocked prompt. No-ops if SLACK_WEBHOOK_URL is unset."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return

    severity = response.severity or "unknown"
    category = response.category or "unknown"
    rule_name = response.matched_rule.name if response.matched_rule else "unknown"
    emoji = SEVERITY_EMOJI.get(severity, ":white_circle:")

    payload = {
        "text": f"{emoji} *PromptShield BLOCK* — {severity.upper()} severity",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} Prompt Injection Blocked"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity.upper()}"},
                    {"type": "mrkdwn", "text": f"*Category:*\n{category}"},
                    {"type": "mrkdwn", "text": f"*Rule:*\n{rule_name}"},
                    {"type": "mrkdwn", "text": f"*Event ID:*\n`{response.event_id}`"},
                ],
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            logger.info("Slack alert sent for event %s", response.event_id)
    except httpx.HTTPStatusError as e:
        logger.warning("Slack webhook returned %s for event %s", e.response.status_code, response.event_id)
    except Exception as e:
        logger.warning("Slack alert failed for event %s: %s", response.event_id, e)
