import json
import logging
from pathlib import Path

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler("hello.log")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)


base = Path(__file__).resolve().parent


class Config(BaseSettings):
    token: str
    channel_id: str
    thread_ts: str = Field("")
    bot_id: str = Field("")

    model_config = SettingsConfigDict(env_file=".env.toml")


def get_bot_id(config: Config) -> tuple[int, str]:
    try:
        r = httpx.get(
            url="https://slack.com/api/auth.test",
            headers={
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    except Exception as e:
        logger.info(f"Error during request: {e}")
        return 1, ""

    if r.status_code != 200:
        logger.info(f"Error: {r.status_code}")
        return 1, ""

    if r.json().get("ok") is not True:
        logger.info(f"Error: {r.json()}")
        return 1, ""

    return 0, r.json().get("user_id")


def get_channel_id(config: Config) -> tuple[int, str]:
    try:
        r = httpx.get(
            url="https://slack.com/api/conversations.list",
            headers={
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    except Exception as e:
        logger.info(f"Error during request: {e}")
        logger.info(f"Error: {e}")
        return 1, ""

    if r.status_code != 200:
        logger.info(f"Error: {r.status_code}")
        return 1, ""

    if r.json().get("ok") is not True:
        logger.info(f"Error: {r.json()}")
        return 1, ""

    with open(base / "response.json", "w") as f:
        json.dump(r.json(), fp=f, indent=2, ensure_ascii=False)

    channels = r.json().get("channels", [])
    id = ""
    for channel in channels:
        if channel["name"] == "일반":
            id = channel["id"]
            break

    if id == "":
        logger.info("No channel named '일반' found")
        return 1, ""

    return 0, id


def check_memeber_of_channel(config: Config) -> int:
    try:
        r = httpx.post(
            url="https://slack.com/api/conversations.members",
            headers={
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/json",
            },
            json={"channel": config.channel_id},
        )
    except Exception as e:
        logger.info(f"Error during request: {e}")
        return 1

    if r.status_code != 200:
        logger.info(f"Error: {r.status_code}")
        return 1

    if r.json().get("ok") is not True:
        logger.info(f"Error: {r.json()}")
        return 1

    is_member = False
    members = r.json().get("members")
    for member in members:
        if member == "U01B2QZG4V7":
            is_member = True
            break

    if not is_member:
        logger.info("Not a member of the channel")
        return 1

    return 0


def join_channel(config: Config) -> int:
    try:
        r = httpx.post(
            url="https://slack.com/api/conversations.join",
            headers={
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/json",
            },
            json={"channel": config.channel_id},
        )
    except Exception as e:
        logger.info(f"Error during request: {e}")
        return 1

    if r.status_code != 200:
        logger.info(f"Error: {r.status_code}")
        return 1

    if r.json().get("ok") is not True:
        logger.info(f"Error: {r.json()}")
        return 1

    return 0


def post_message(config: Config) -> tuple[int, str]:
    try:
        r = httpx.post(
            url="https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/json",
            },
            json={"channel": config.channel_id, "text": "Hello, World!"},
        )
    except Exception as e:
        logger.info(f"Error during request: {e}")
        return 1, ""

    logger.info(r.json())
    with open(base / "response2.json", "w") as f:
        json.dump(r.json(), fp=f, indent=2, ensure_ascii=False)

    ts = r.json().get("message").get("ts")

    return 0, ts


def post_comments(config: Config):
    try:
        r = httpx.post(
            url="https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/json",
            },
            json={
                "channel": config.channel_id,
                "text": "Hello, World!",
                "thread_ts": config.thread_ts,
            },
        )
    except Exception as e:
        logger.info(f"Error during request: {e}")
        return 1, ""

    if r.status_code != 200:
        logger.info(f"Error: {r.status_code}")
        return 1

    if r.json().get("ok") is not True:
        logger.info(f"Error: {r.json()}")
        return 1

    return 0


if __name__ == "__main__":
    config = Config()
    if not config.bot_id:
        ret, id = get_bot_id(config)

        if ret != 0:
            exit(1)
        config.bot_id = id

    if not config.channel_id:
        ret, id = get_channel_id(config)

        if ret != 0:
            exit(1)
        config.channel_id = id

    is_member = check_memeber_of_channel(config)
    if is_member != 0:
        ret = join_channel(config)
        if ret != 0:
            exit(1)

    ts = post_message(config)
    config.thread_ts = ts
    post_comments(config)

    logger.info("Done")
