from bot.ai_engine import Engine
import telebot
import os
import re
import logging
import html
from colorama import Fore, Style, init

init(autoreset=True)

# ===== Logging Setup =====
class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.DEBUG: Fore.CYAN,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, Fore.WHITE)
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

logger = logging.getLogger("AI_BOT")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter("[%(asctime)s] [%(levelname)s] %(message)s"))
logger.addHandler(handler)

def sanitize_html(text: str) -> str:
    if not text:
        return "Empty response."
    return html.escape(text)

# ===== Chat History =====
chat_history = {}

# ===== Main =====
def main():
    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not found in environment variables.")
        return

    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    ai_client = Engine()

    logger.info("Bot started successfully.")

    # ===== /start =====
    @bot.message_handler(commands=['start'])
    def start(message):
        chat_history[message.chat.id] = []
        first_name = message.from_user.first_name or "there"

        logger.info(f"New session started | User: {first_name} | Chat ID: {message.chat.id}")

        welcome_text = (
            f"*Welcome, {first_name}!* 👋\n\n"
            "I'm your AI assistant.\n\n"
            "*Available commands:*\n"
            "• `/start` — restart session\n"
            "• `/clear` — clear chat history\n\n"
            "Just send me a message to begin."
        )

        bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

    # ===== /clear =====
    @bot.message_handler(commands=['clear'])
    def clear(message):
        chat_history[message.chat.id] = []
        logger.info(f"Chat history cleared | Chat ID: {message.chat.id}")
        bot.send_message(message.chat.id, "Chat history cleared.", parse_mode="Markdown")

    # ===== Message Handler =====
    @bot.message_handler(func=lambda message: True)
    def get_answer(message):
        text = (message.text or "").strip()

        if not text:
            logger.warning(f"Empty message received | Chat ID: {message.chat.id}")
            bot.reply_to(message, "Please enter a valid message.", parse_mode="Markdown")
            return

        if message.chat.id not in chat_history:
            chat_history[message.chat.id] = []

        chat_history[message.chat.id].append({"role": "user", "content": text})

        logger.info(f"User message | Chat ID: {message.chat.id} | Length: {len(text)} chars")

        bot.send_chat_action(message.chat.id, 'typing')

        try:
            response = ai_client.get_reply(message.text, chat_history=chat_history[message.chat.id])
            logger.info(f"AI response generated | Chat ID: {message.chat.id}")
        except Exception as e:
            logger.error(f"AI Engine Error | Chat ID: {message.chat.id} | Error: {e}")
            response = "Something went wrong while generating a response."

        safe_response = sanitize_html(response)
        bot.reply_to(message, safe_response, parse_mode="HTML")

        chat_history[message.chat.id].append({"role": "assistant", "content": response})

    bot.polling(none_stop=True)

