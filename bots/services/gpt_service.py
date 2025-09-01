import openai
import tiktoken
import logging
from typing import List, Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class GPTService:
    """Сервис для работы с OpenAI GPT API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация сервиса

        Args:
            api_key: API ключ OpenAI. Если не указан, используется из настроек
        """
        self.api_key = api_key or getattr(settings, "OPENAI_API_KEY", None)
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        # Настройка клиента OpenAI
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)

    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Подсчет токенов в тексте

        Args:
            text: Текст для подсчета
            model: Модель GPT

        Returns:
            Количество токенов
        """
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}")
            # Приблизительная оценка: 1 токен ≈ 4 символа
            return len(text) // 4

    def count_messages_tokens(
        self, messages: List[Dict], model: str = "gpt-3.5-turbo"
    ) -> int:
        """
        Подсчет токенов в массиве сообщений

        Args:
            messages: Массив сообщений в формате OpenAI
            model: Модель GPT

        Returns:
            Общее количество токенов
        """
        total_tokens = 0
        for message in messages:
            # Токены за роль и контент
            total_tokens += self.count_tokens(message.get("role", ""), model)
            total_tokens += self.count_tokens(message.get("content", ""), model)
            # Дополнительные токены за структуру сообщения
            total_tokens += 4

        # Дополнительные токены за весь запрос
        total_tokens += 2
        return total_tokens

    def trim_messages(
        self, messages: List[Dict], max_tokens: int, model: str = "gpt-3.5-turbo"
    ) -> List[Dict]:
        """
        Обрезка сообщений для соблюдения лимита токенов

        Args:
            messages: Массив сообщений
            max_tokens: Максимальное количество токенов
            model: Модель GPT

        Returns:
            Обрезанный массив сообщений
        """
        if not messages:
            return messages

        # Системное сообщение всегда сохраняем
        system_message = None
        user_messages = []

        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg
            else:
                user_messages.append(msg)

        # Начинаем с системного сообщения
        result = [system_message] if system_message else []
        current_tokens = self.count_messages_tokens(result, model)

        # Добавляем сообщения с конца (самые новые)
        for msg in reversed(user_messages):
            msg_tokens = self.count_tokens(msg.get("content", ""), model) + 4
            if current_tokens + msg_tokens <= max_tokens:
                result.insert(-1 if system_message else 0, msg)
                current_tokens += msg_tokens
            else:
                break

        return result

    def generate_response(
        self,
        messages: List[Dict],
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        max_context_tokens: int = 3000,
    ) -> Dict:
        """
        Генерация ответа от GPT

        Args:
            messages: Массив сообщений в формате OpenAI
            model: Модель GPT
            max_tokens: Максимум токенов в ответе
            temperature: Температура (креативность)
            max_context_tokens: Максимум токенов в контексте

        Returns:
            Словарь с ответом и метаданными
        """
        try:
            # Обрезаем сообщения если нужно
            trimmed_messages = self.trim_messages(messages, max_context_tokens, model)

            logger.info(f"Sending request to OpenAI: {len(trimmed_messages)} messages")

            # Отправляем запрос к OpenAI
            response = self.client.chat.completions.create(
                model=model,
                messages=trimmed_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30,
            )

            # Извлекаем данные из ответа
            content = response.choices[0].message.content
            usage = response.usage

            logger.info(f"OpenAI response received: {usage.total_tokens} tokens used")

            return {
                "success": True,
                "content": content,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                },
                "model": model,
            }

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            return {
                "success": False,
                "error": "rate_limit",
                "message": "Превышен лимит запросов к GPT. Попробуйте позже.",
            }

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {e}")
            return {
                "success": False,
                "error": "auth_error",
                "message": "Ошибка аутентификации OpenAI API.",
            }

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                "success": False,
                "error": "api_error",
                "message": "Ошибка OpenAI API. Попробуйте позже.",
            }

        except Exception as e:
            logger.error(f"Unexpected error in GPT service: {e}")
            return {
                "success": False,
                "error": "unknown_error",
                "message": "Произошла неожиданная ошибка. Попробуйте позже.",
            }
