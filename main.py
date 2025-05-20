# - *- coding: utf- 8 - *-
import asyncio
import os
import sys

import colorama
from aiogram import Dispatcher, Bot, types
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from tgbot.data.config import get_admins, BOT_TOKEN, BOT_SCHEDULER
from tgbot.database.db_helper import create_dbx
from tgbot.middlewares import register_all_middlwares
from tgbot.routers import register_all_routers
from tgbot.services.api_session import AsyncRequestSession
from tgbot.utils.misc.bot_commands import set_commands
from tgbot.utils.misc.bot_logging import bot_logger
from tgbot.utils.misc.bot_models import ARS
from tgbot.utils.misc_functions import (check_update, check_bot_username, startup_notify, update_profit_day,
                                        update_profit_week, autobackup_admin, check_mail, update_profit_month,
                                        autosettings_unix)

colorama.init()

# Конфигурация вебхука
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.environ.get("https://softvaultbot.onrender.com/webhook") + WEBHOOK_PATH  # Пример: https://your-bot.onrender.com/webhook

# Запуск шедулеров
async def scheduler_start(bot: Bot, arSession: ARS):
    BOT_SCHEDULER.add_job(update_profit_month, trigger="cron", day=1, hour=0, minute=0, second=5)
    BOT_SCHEDULER.add_job(update_profit_week, trigger="cron", day_of_week="mon", hour=0, minute=0, second=10)
    BOT_SCHEDULER.add_job(update_profit_day, trigger="cron", hour=0, minute=0, second=15, args=(bot,))
    BOT_SCHEDULER.add_job(autobackup_admin, trigger="cron", hour=0, args=(bot,))
    BOT_SCHEDULER.add_job(check_update, trigger="cron", hour=0, args=(bot, arSession,))
    BOT_SCHEDULER.add_job(check_mail, trigger="cron", hour=12, args=(bot, arSession,))


# Запуск бота и веб-сервера
async def main():
    BOT_SCHEDULER.start()
    dp = Dispatcher()
    arSession = AsyncRequestSession()
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    register_all_middlwares(dp)
    register_all_routers(dp)

    try:
        await autosettings_unix()
        await set_commands(bot)
        await check_bot_username(bot)
        await check_update(bot, arSession)
        await check_mail(bot, arSession)
        await startup_notify(bot, arSession)
        await scheduler_start(bot, arSession)

        bot_logger.warning("BOT WAS STARTED")
        print(colorama.Fore.LIGHTYELLOW_EX + f"~~~~~ Bot was started - @{(await bot.get_me()).username} ~~~~~")
        print(colorama.Fore.LIGHTBLUE_EX + "~~~~~ TG developer - @dx1one ~~~~~")
        print(colorama.Fore.RESET)

        if len(get_admins()) == 0:
            print("***** ENTER ADMIN ID IN settings.ini *****")

        await bot.delete_webhook()
        await bot.set_webhook(url=WEBHOOK_URL)  # Установка вебхука

        # Настройка aiohttp сервера
        app = web.Application()
        SimpleRequestHandler(dp, bot).register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
        await site.start()

        # Бесконечное ожидание
        await asyncio.Event().wait()

    finally:
        await arSession.close()
        await bot.session.close()


if __name__ == "__main__":
    create_dbx()

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        bot_logger.warning("Bot was stopped")
    finally:
        if sys.platform.startswith("win"):
            os.system("cls")
        else:
            os.system("clear")