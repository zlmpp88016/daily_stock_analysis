import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import Config, setup_env
from src.notification_sender.discord_sender import DiscordSender


def _env_flag_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _build_discord_config_from_env() -> Config:
    setup_env(override=True)
    return Config(
        stock_list=["000001"],
        discord_bot_token=os.getenv("DISCORD_BOT_TOKEN"),
        discord_main_channel_id=os.getenv("DISCORD_MAIN_CHANNEL_ID"),
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        discord_max_words=int(os.getenv("DISCORD_MAX_WORDS", "2000")),
        webhook_verify_ssl=_env_bool("WEBHOOK_VERIFY_SSL", default=True),
    )


@pytest.mark.network
def test_send_to_discord_with_env_live_config():
    if not _env_flag_enabled("RUN_DISCORD_LIVE_TEST"):
        pytest.skip("Set RUN_DISCORD_LIVE_TEST=1 to run the live Discord notification test.")

    config = _build_discord_config_from_env()
    sender = DiscordSender(config)

    if not sender._is_discord_configured():
        pytest.skip("Discord is not configured in .env.")

    message = (
        "[daily_stock_analysis] Discord live test\n"
        f"time={datetime.now(timezone.utc).isoformat()}\n"
        f"nonce={uuid4()}"
    )

    assert sender.send_to_discord(message) is True
