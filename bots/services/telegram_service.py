import asyncio
import logging
import time
from typing import Dict, Optional
from telegram import Bot as TelegramBot, Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from django.utils import timezone
from ..models import Bot, TelegramUser, Conversation
from .gpt_service import GPTService

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Сервис для работы с Telegram ботом в polling режиме"""

    def __init__(self, bot_instance: Bot):
        """
        Инициализация сервиса

        Args:
            bot_instance: Экземпляр модели Bot
        """
        self.bot_instance = bot_instance
        self.telegram_bot = TelegramBot(token=bot_instance.telegram_token)
        self.gpt_service = GPTService(api_key=bot_instance.gpt_api_key)
        self.application = None
        self.is_running = False

    async def setup_application(self):
        """Настройка Telegram Application"""
        self.application = (
            Application.builder().token(self.bot_instance.telegram_token).build()
        )

        # Добавляем обработчики команд
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("help", self.handle_help))
        self.application.add_handler(CommandHandler("clear", self.handle_clear))
        self.application.add_handler(CommandHandler("settings", self.handle_settings))

        # Добавляем обработчик текстовых сообщений
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        logger.info(f"Bot '{self.bot_instance.name}' application configured")

    def get_or_create_telegram_user(self, telegram_user_data) -> TelegramUser:
        """Получить или создать пользователя Telegram"""
        user, created = TelegramUser.objects.get_or_create(
            telegram_id=telegram_user_data.id,
            defaults={
                "username": telegram_user_data.username,
                "first_name": telegram_user_data.first_name or "",
                "last_name": telegram_user_data.last_name or "",
                "is_bot": telegram_user_data.is_bot,
            },
        )

        # Обновляем данные пользователя если они изменились
        if not created:
            updated = False
            if user.username != telegram_user_data.username:
                user.username = telegram_user_data.username
                updated = True
            if user.first_name != (telegram_user_data.first_name or ""):
                user.first_name = telegram_user_data.first_name or ""
                updated = True
            if user.last_name != (telegram_user_data.last_name or ""):
                user.last_name = telegram_user_data.last_name or ""
                updated = True

            if updated:
                user.save()

        return user

    def get_or_create_conversation(self, telegram_user: TelegramUser) -> Conversation:
        """Получить или создать диалог"""
        conversation, created = Conversation.objects.get_or_create(
            bot=self.bot_instance,
            telegram_user=telegram_user,
            defaults={"is_active": True},
        )
        return conversation

    async def handle_start(self, update: Update, context) -> None:
        """Обработчик команды /start"""
        user = self.get_or_create_telegram_user(update.effective_user)
        conversation = self.get_or_create_conversation(user)

        welcome_message = (
            f"👋 Привет! Я {self.bot_instance.name}.\n\n"
            f"{self.bot_instance.description}\n\n"
            "Просто напиши мне сообщение, и я отвечу с помощью GPT!\n\n"
            "Доступные команды:\n"
            "/help - справка\n"
            "/clear - очистить историю диалога\n"
            "/settings - настройки бота"
        )

        await update.message.reply_text(welcome_message)
        logger.info(
            f"User {user} started conversation with bot {self.bot_instance.name}"
        )

    async def handle_help(self, update: Update, context) -> None:
        """Обработчик команды /help"""
        help_message = (
            f"🤖 {self.bot_instance.name}\n\n"
            f"Описание: {self.bot_instance.description}\n\n"
            "📋 Доступные команды:\n"
            "/start - начать диалог\n"
            "/help - показать эту справку\n"
            "/clear - очистить историю диалога\n"
            "/settings - показать настройки бота\n\n"
            "💬 Просто напишите мне любое сообщение, и я отвечу с помощью GPT!"
        )

        await update.message.reply_text(help_message)

    async def handle_clear(self, update: Update, context) -> None:
        """Обработчик команды /clear"""
        user = self.get_or_create_telegram_user(update.effective_user)
        conversation = self.get_or_create_conversation(user)

        conversation.clear_history()

        await update.message.reply_text(
            "🗑️ История диалога очищена! Можете начать новый разговор."
        )
        logger.info(f"User {user} cleared conversation history")

    async def handle_settings(self, update: Update, context) -> None:
        """Обработчик команды /settings"""
        settings_message = (
            f"⚙️ Настройки бота {self.bot_instance.name}:\n\n"
            f"🤖 GPT модель: {self.bot_instance.gpt_model}\n"
            f"🎯 Максимум токенов: {self.bot_instance.max_tokens}\n"
            f"🌡️ Температура: {self.bot_instance.temperature}\n\n"
            f"📝 Системный промпт:\n{self.bot_instance.system_prompt}"
        )

        await update.message.reply_text(settings_message)

    async def handle_message(self, update: Update, context) -> None:
        """Обработчик текстовых сообщений"""
        try:
            # Показываем индикатор "печатает..."
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )

            user = self.get_or_create_telegram_user(update.effective_user)
            conversation = self.get_or_create_conversation(user)

            user_message = update.message.text
            logger.info(f"Received message from {user}: {user_message[:50]}...")

            # Добавляем сообщение пользователя в диалог
            conversation.add_message("user", user_message)

            # Получаем сообщения для GPT
            messages = conversation.get_openai_messages()

            # Отправляем запрос к GPT
            gpt_response = self.gpt_service.generate_response(
                messages=messages,
                model=self.bot_instance.gpt_model,
                max_tokens=self.bot_instance.max_tokens,
                temperature=self.bot_instance.temperature,
            )

            if gpt_response["success"]:
                # Успешный ответ от GPT
                bot_message = gpt_response["content"]

                # Добавляем ответ бота в диалог
                conversation.add_message("assistant", bot_message)

                # Обновляем счетчик токенов
                conversation.total_tokens += gpt_response["usage"]["total_tokens"]
                conversation.save()

                # Отправляем ответ пользователю
                await update.message.reply_text(bot_message)

                logger.info(f"Sent GPT response to {user}: {bot_message[:50]}...")
                logger.info(f"Tokens used: {gpt_response['usage']['total_tokens']}")

            else:
                # Ошибка от GPT
                error_message = f"❌ {gpt_response['message']}"
                await update.message.reply_text(error_message)
                logger.error(f"GPT error for user {user}: {gpt_response}")

        except Exception as e:
            logger.error(f"Error handling message from {update.effective_user.id}: {e}")
            await update.message.reply_text(
                "😔 Произошла ошибка при обработке сообщения. Попробуйте позже."
            )

    async def start_polling(self):
        """Запуск polling режима"""
        if self.is_running:
            logger.warning(f"Bot {self.bot_instance.name} is already running")
            return

        try:
            await self.setup_application()

            logger.info(f"Starting bot '{self.bot_instance.name}' in polling mode...")
            self.is_running = True

            # Запускаем polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                drop_pending_updates=True, allowed_updates=["message", "callback_query"]
            )

            logger.info(f"Bot '{self.bot_instance.name}' started successfully")

            # Ждем пока бот работает
            while self.is_running and self.bot_instance.is_active:
                await asyncio.sleep(1)

                # Обновляем данные бота из БД
                self.bot_instance.refresh_from_db()

        except Exception as e:
            logger.error(f"Error starting bot {self.bot_instance.name}: {e}")
            self.is_running = False
        finally:
            await self.stop_polling()

    async def stop_polling(self):
        """Остановка polling режима"""
        if not self.is_running:
            return

        logger.info(f"Stopping bot '{self.bot_instance.name}'...")
        self.is_running = False

        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.error(f"Error stopping bot {self.bot_instance.name}: {e}")

        logger.info(f"Bot '{self.bot_instance.name}' stopped")


class TelegramBotManager:
    """Менеджер для управления несколькими Telegram ботами"""

    def __init__(self):
        self.bot_services: Dict[int, TelegramBotService] = {}
        self.is_running = False

    async def start_all_bots(self):
        """Запуск всех активных ботов"""
        if self.is_running:
            logger.warning("Bot manager is already running")
            return

        self.is_running = True
        active_bots = Bot.objects.filter(is_active=True)

        logger.info(f"Starting {active_bots.count()} active bots...")

        # Создаем задачи для каждого бота
        tasks = []
        for bot in active_bots:
            try:
                service = TelegramBotService(bot)
                self.bot_services[bot.id] = service
                task = asyncio.create_task(service.start_polling())
                tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to start bot {bot.name}: {e}")

        if tasks:
            # Ждем завершения всех задач
            await asyncio.gather(*tasks, return_exceptions=True)

        self.is_running = False
        logger.info("All bots stopped")

    async def stop_all_bots(self):
        """Остановка всех ботов"""
        logger.info("Stopping all bots...")
        self.is_running = False

        # Останавливаем все сервисы
        stop_tasks = []
        for service in self.bot_services.values():
            stop_tasks.append(service.stop_polling())

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        self.bot_services.clear()
        logger.info("All bots stopped")
