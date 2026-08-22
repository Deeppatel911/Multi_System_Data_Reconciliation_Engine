from dotenv import load_dotenv
from slack_sdk import WebClient
import os

load_dotenv()


def send_discrepancy_alert(state: dict, thread_id: str, channel: str = "#new-channel"):
    """
    Post a Slack alert summarizing the discrepancies found in a reconciliation run,
    with interactive buttons to approve or reject the proposed resolution.
    """
    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚨 Data Discrepancy Detected",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Entity:* {state['query']}\n"
                    f"*Thread ID:* {thread_id}\n"
                    f"*Canonical ID:* {state['canonical_profile'].canonical_id}"
                ),
            },
        },
        {"type": "divider"},
    ]

    for disc in state["discrepancies"]:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Conflict in field: `{disc.field_name}`*\n"
                        f"{disc.conflict_description}"
                    ),
                },
            }
        )
        blocks.append(
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*{source}:*\n{value}"}
                    for source, value in disc.conflicting_values.items()
                ],
            }
        )
        blocks.append({"type": "divider"})

    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Approve & Persist"},
                    "style": "primary",
                    "action_id": "approve_resolution",
                    "value": "approve",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Reject (Halt)"},
                    "style": "danger",
                    "action_id": "reject_resolution",
                    "value": "reject",
                },
            ],
        }
    )

    return client.chat_postMessage(channel=channel, blocks=blocks, text="Discrepancy alert")
