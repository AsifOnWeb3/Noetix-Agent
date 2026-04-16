"""
NoetixAgent Messaging Gateway — Telegram + Discord support.
Inspired by OpenClaw and Hermes gateway architecture.
"""

import asyncio
import logging
import threading
from typing import Optional, Callable

logger = logging.getLogger("noetix.gateway")


class TelegramGateway:
    """Telegram bot gateway using python-telegram-bot."""

    def __init__(self, token: str, run_task: Callable, allowed_users: list = None):
        self.token = token
        self.run_task = run_task
        self.allowed_users = allowed_users or []

    def start(self):
        try:
            from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, Application

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            app: Application = ApplicationBuilder().token(self.token).build()

            async def start_cmd(update, context):
                await update.message.reply_text("NoetixAgent ready. Send me a task!")

            async def handle_msg(update, context):
                user_id = update.effective_user.id
                if self.allowed_users and user_id not in self.allowed_users:
                    await update.message.reply_text("Unauthorized.")
                    return
                text = update.message.text
                await update.message.reply_text("Processing...")
                result = self.run_task(text)
                for i in range(0, len(result), 4000):
                    await update.message.reply_text(result[i:i+4000])

            app.add_handler(CommandHandler("start", start_cmd))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

            async def run():
                await app.initialize()
                await app.start()
                await app.updater.start_polling(drop_pending_updates=True)
                logger.info("Telegram gateway running.")
                await asyncio.Event().wait()  # block forever

            loop.run_until_complete(run())

        except ImportError:
            logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
        except Exception as e:
            logger.error(f"Telegram gateway error: {e}")


class DiscordGateway:
    """Discord bot gateway."""

    def __init__(self, token: str, run_task: Callable, allowed_channels: list = None):
        self.token = token
        self.run_task = run_task
        self.allowed_channels = allowed_channels or []

    def start(self):
        try:
            import discord

            intents = discord.Intents.default()
            intents.message_content = True
            client = discord.Client(intents=intents)

            @client.event
            async def on_ready():
                logger.info(f"Discord gateway online as {client.user}")

            @client.event
            async def on_message(message):
                if message.author == client.user:
                    return
                if self.allowed_channels and message.channel.id not in self.allowed_channels:
                    return
                if not message.content.startswith("!noetix "):
                    return
                task = message.content[8:]
                await message.channel.send("Processing...")
                result = self.run_task(task)
                for i in range(0, len(result), 2000):
                    await message.channel.send(result[i:i+2000])

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(client.start(self.token))

        except ImportError:
            logger.error("discord.py not installed. Run: pip install discord.py")


class GatewayServer:
    """Unified gateway — starts configured messaging backends."""

    def __init__(self, agent):
        self.agent = agent
        self.config = agent.config.gateway

    def start(self):
        threads = []

        if self.config.get("telegram", {}).get("enabled"):
            token = self.config["telegram"].get("bot_token") or ""
            if token:
                gw = TelegramGateway(token, self.agent.run_task)
                t = threading.Thread(target=gw.start, daemon=True)
                t.start()
                threads.append(t)
                logger.info("Telegram gateway thread started.")

        if self.config.get("discord", {}).get("enabled"):
            token = self.config["discord"].get("token") or ""
            if token:
                gw = DiscordGateway(token, self.agent.run_task)
                t = threading.Thread(target=gw.start, daemon=True)
                t.start()
                threads.append(t)
                logger.info("Discord gateway thread started.")

        if not threads:
            logger.warning("No gateways enabled. Check config.")
            return

        for t in threads:
            t.join()
