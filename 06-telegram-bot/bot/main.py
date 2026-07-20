import logging
import sys

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from .api_client import ApiClient
from .config import Config
from .handlers import build_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    cfg = Config()
    if not cfg.bot_token:
        print("Set MD_BOT_TOKEN (from @BotFather) first.", file=sys.stderr)
        sys.exit(1)

    api = ApiClient(cfg.api_url, cfg.api_key)
    handlers = build_handlers(cfg, api)

    app = Application.builder().token(cfg.bot_token).build()
    app.add_handler(CommandHandler("start", handlers["start"]))
    app.add_handler(CommandHandler("help", handlers["start"]))
    app.add_handler(CommandHandler("id", handlers["id"]))
    app.add_handler(CommandHandler("formats", handlers["formats"]))
    app.add_handler(MessageHandler(filters.Document.ALL, handlers["document"]))
    app.add_handler(MessageHandler(filters.PHOTO, handlers["photo"]))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers["text"]))

    logging.getLogger(__name__).info("md-converter bot polling (API: %s)", cfg.api_url)
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
