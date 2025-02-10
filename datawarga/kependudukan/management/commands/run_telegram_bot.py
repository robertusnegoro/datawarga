from django.core.management.base import BaseCommand
from django.conf import settings
from kependudukan.telegram_bot import run_telegram_bot

class Command(BaseCommand):
    help = 'Runs the Telegram bot'

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stdout.write(self.style.ERROR('Error: TELEGRAM_BOT_TOKEN not configured'))
            return
            
        if not settings.BOT_API_USER or not settings.BOT_API_PASS:
            self.stdout.write(self.style.ERROR('Error: Bot API credentials not configured'))
            return
            
        if not settings.SITE_URL:
            self.stdout.write(self.style.ERROR('Error: SITE_URL not configured'))
            return

        self.stdout.write(self.style.SUCCESS('Starting Telegram bot...'))
        run_telegram_bot() 