import os


class Config:
    def __init__(self) -> None:
        self.bot_token = os.getenv("MD_BOT_TOKEN", "")
        self.api_url = os.getenv("MD_API_URL", "http://127.0.0.1:8460").rstrip("/")
        self.api_key = os.getenv("MD_API_KEY", "")
        ids = os.getenv("MD_BOT_ALLOWED_IDS", "")
        # Empty allowlist = open bot (fine for private testing; set ids before
        # exposing the token anywhere).
        self.allowed_ids = {int(x) for x in ids.split(",") if x.strip().isdigit()}

    def allowed(self, user_id: int | None) -> bool:
        if not self.allowed_ids:
            return True
        return user_id is not None and user_id in self.allowed_ids
