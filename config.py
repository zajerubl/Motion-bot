import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def get_int_env(key: str, default: int = 0) -> int:
    val = os.getenv(key, str(default)).strip()
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip().strip('"').strip("'")
    ADMIN_ID: int = get_int_env("ADMIN_ID", 0)
    CONTACT_USERNAME: str = os.getenv("CONTACT_USERNAME", "shantrapaev").replace("@", "").strip()
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "").strip()
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "zajerubl/Motion-bot").strip()

config = Config()

def is_admin(user) -> bool:
    if not user:
        return False
    if config.ADMIN_ID and user.id == config.ADMIN_ID:
        return True
    if user.username and user.username.lower() == config.CONTACT_USERNAME.lower():
        if config.ADMIN_ID == 0:
            config.ADMIN_ID = user.id
        return True
    return False
