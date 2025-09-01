import asyncio
import signal
import sys
import logging
from django.core.management.base import BaseCommand

# from django.conf import settings
from bots.services.telegram_service import TelegramBotManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("telegram_bots.log"),
    ],
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Запуск Telegram ботов"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot_manager = TelegramBotManager()
        self.shutdown_requested = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--bot-id",
            type=int,
            help="ID конкретного бота для запуска (по умолчанию запускаются все активные)",
        )

    def handle_shutdown(self, signum, frame):
        """Обработчик сигналов"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown_requested = True

    def handle(self, *args, **options):
        """Основной метод"""
        bot_id = options.get("bot_id")

        # Настраиваем обработчики сигналов
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        if bot_id:
            self.stdout.write(f"Запуск бота с ID: {bot_id}")
        else:
            self.stdout.write("Запуск всех активных ботов...")

        try:
            # Запускаем event loop
            asyncio.run(self.run_bots(bot_id))
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.stderr.write(f"Ошибка: {e}")
        finally:
            self.stdout.write("Все боты остановлены")

    async def run_bots(self, bot_id=None):
        """Запуск ботов в асинхронном режиме"""
        try:
            if bot_id:
                # Запуск конкретного бота
                from bots.models import Bot

                try:
                    bot = Bot.objects.get(id=bot_id, is_active=True)
                    from bots.services.telegram_service import TelegramBotService

                    service = TelegramBotService(bot)
                    await service.start_polling()
                except Bot.DoesNotExist:
                    self.stderr.write(f"Активный бот с ID {bot_id} не найден")
                    return
            else:
                # Запуск всех активных ботов
                await self.bot_manager.start_all_bots()

        except Exception as e:
            logger.error(f"Error running bots: {e}")
        finally:
            # Останавливаем все боты при завершении
            await self.bot_manager.stop_all_bots()
