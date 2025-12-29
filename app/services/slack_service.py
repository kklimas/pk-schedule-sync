import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.config import config

logger = logging.getLogger(__name__)

class SlackService:
    def __init__(self):
        self.token = config.SLACK_BOT_TOKEN
        self.default_channel = config.SLACK_CHANNEL
        self.status_channel = config.SLACK_CHANNEL_JOB_STATUS
        self.client = WebClient(token=self.token) if self.token else None
        
        # Format mentions: <@U123>, <@U456>
        raw_mentions = config.SLACK_MENTIONS or ""
        self.mentions = " ".join([f"<@{m.strip()}>" for m in raw_mentions.split(",") if m.strip()])

        if not self.token:
            logger.warning("SLACK_BOT_TOKEN not provided. Slack notifications will be disabled.")

    def _get_timestamp_block(self):
        warsaw_now = datetime.now(ZoneInfo("Europe/Warsaw")).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🕒 *Local Time:* {warsaw_now}"
                }
            ]
        }

    def send_job_status(self, title: str, status: str, message: str):
        """
        Sends a job status notification to the status channel.
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title,
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Status:* {status}\n*Message:* {message}"
                }
            }
        ]

        if status.lower() == "failed" and self.mentions:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚨 Attention: {self.mentions}"
                }
            })

        blocks.append(self._get_timestamp_block())
        return self._send_blocks(self.status_channel, blocks, f"{title}: {status}")

    def send_schedule_update(self, title: str, message: str, added: list = None, updated: list = None, deleted: list = None, sheet_url: str = None):
        """
        Sends a schedule update notification with categorized lecture details.
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title,
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]

        if self.mentions:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📢 CC: {self.mentions}"
                }
            })

        if sheet_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📁 Download Original Sheet",
                            "emoji": True
                        },
                        "url": sheet_url,
                        "action_id": "download_sheet"
                    }
                ]
            })

        def add_category_section(label, items, emoji):
            if not items:
                return
            
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *{label}*"
                }
            })
            
            # Limit per category to avoid block limits
            for lecture in items[:5]:
                def get_val(obj, key):
                    if isinstance(obj, dict):
                        return obj.get(key)
                    return getattr(obj, key, None)

                l_date = get_val(lecture, 'date')
                l_start = get_val(lecture, 'start_time')
                l_subject = get_val(lecture, 'subject')
                l_summary = get_val(lecture, 'summary')
                l_room = get_val(lecture, 'room')

                lecture_info = f"• *{l_date}* {l_start} — {l_subject or l_summary}"
                if l_room:
                    lecture_info += f" (_Room: {l_room}_)"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": lecture_info
                    }
                })
            
            if len(items) > 5:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"_And {len(items) - 5} more..._"
                        }
                    ]
                })

        add_category_section("New Lectures", added, "✨")
        add_category_section("Updated Details", updated, "📝")
        add_category_section("Cancelled Lectures", deleted, "🚫")

        blocks.append(self._get_timestamp_block())
        return self._send_blocks(self.default_channel, blocks, title)

    def _send_blocks(self, channel: str, blocks: list, fallback_text: str):
        if not self.client:
            return

        try:
            response = self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=fallback_text
            )
            logger.info(f"Slack blocks sent successfully to {channel}")
            return response
        except SlackApiError as e:
            logger.error(f"Error sending Slack blocks to {channel}: {e.response['error']}")
            return None

slack_service = SlackService()
