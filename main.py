import re
import imaplib
import email
from email.utils import parsedate_to_datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import os
import logging
import json
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
EMAIL_CREDENTIALS = json.loads(os.getenv("EMAIL_CREDENTIALS", "{}")) 
if not TELEGRAM_BOT_TOKEN or not EMAIL_CREDENTIALS:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN or EMAIL_CREDENTIALS in environment variables.")

print("Environment variables loaded successfully!")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Global dictionary to store user-provided email temporarily
user_email = {}

def fetch_latest_otp(email_user, email_pass):
    try:
        # Connect to the email server
        if "gmail.com" in email_user:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
        elif "outlook.com" in email_user or "hotmail.com" in email_user:
            mail = imaplib.IMAP4_SSL("imap-mail.outlook.com")
        else:
            raise ValueError("Unsupported email provider.")
        mail.login(email_user, email_pass)
        mail.select('inbox')

        # Search for all emails
        status, messages = mail.search(None, 'ALL')
        email_ids = messages[0].split()

        # Process emails from latest to oldest
        for email_id in reversed(email_ids):
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Retrieve the email body
                    email_body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get('Content-Disposition'))
                            if 'attachment' not in content_disposition:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    if content_type == "text/plain":
                                        email_body = payload.decode()
                                    elif content_type == "text/html":
                                        email_body = payload.decode()  # Optionally parse HTML
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            email_body = payload.decode()
                    if email_body:
                        email_body = re.sub(r'<[^>]+>', '', email_body).strip()

                    # Search for a 6-digit OTP code in the email body
                    otp_match = re.search(r'\b\d{6}\b', email_body)
                    if otp_match:
                        otp_code = otp_match.group(0)

                        # Get the email sent time
                        date_header = msg.get('Date')
                        email_time = None
                        if date_header:
                            email_time = parsedate_to_datetime(date_header)

                        mail.logout()
                        return otp_code, email_time

        mail.logout()
        return None, None
    except Exception as e:
        logging.error(f"Error fetching OTP: {str(e)}")
        return None, None

async def start_command(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! I'm your bot. Use /help to see available commands.")

# Help command
async def help_command(update: Update, context: CallbackContext):
    commands = """
Here are the available commands:
/start - Start the bot
/help - Show this help message
/status - Get the bot status
/fetch - Fetch the latest OTP code (you'll need to provide your email)
    """
    await update.message.reply_text(commands)

# Status command
async def status_command(update: Update, context: CallbackContext):
    await update.message.reply_text("The bot is running and ready to assist you!")

# Fetch command
async def fetch_command(update: Update, context: CallbackContext):
    await update.message.reply_text("Please provide your email address to fetch the latest OTP code.")

async def handle_email(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    provided_email = update.message.text.strip()

    # Check if the email is in predefined credentials
    if provided_email in EMAIL_CREDENTIALS:
        user_email[user_id] = provided_email
        await update.message.reply_text(
            f"Email '{provided_email}' recognized. Fetching your latest OTP code..."
        )

        # Fetch the latest OTP code
        email_pass = EMAIL_CREDENTIALS[provided_email]
        otp_code, email_time = fetch_latest_otp(provided_email, email_pass)

        if otp_code:
            if email_time:
                await update.message.reply_text(
                    f"OTP code is: {otp_code}\n\nReceived on: {email_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                await update.message.reply_text(f"OTP code is: {otp_code}")
        else:
            await update.message.reply_text("No OTP code found in your recent emails.")
    else:
        await update.message.reply_text(
            "Sorry, the provided email address is not recognized. Please try again with a valid email."
        )

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
    # Create the bot application
    application = Application.builder().token(token).build()

    # Add command handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email))
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('fetch', fetch_command))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
