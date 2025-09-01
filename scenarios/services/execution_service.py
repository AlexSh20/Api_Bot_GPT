import logging
from typing import Dict, Any, Optional, Tuple
from django.utils import timezone
from ..models import Scenario, Step
from bots.models import Bot, TelegramUser, UserScenarioSession
from bots.services.gpt_service import GPTService

logger = logging.getLogger(__name__)


class ScenarioExecutionService:
    """Сервис для выполнения сценариев взаимодействия"""

    def __init__(self):
        self.gpt_service = GPTService()

    def start_scenario(
        self,
        bot: Bot,
        telegram_user: TelegramUser,
        scenario: Scenario,
        context_data: Dict[str, Any] = None,
    ) -> UserScenarioSession:
        """
        Запустить сценарий для пользователя

        Args:
            bot: Экземпляр бота
            telegram_user: Пользователь Telegram
            scenario: Сценарий для запуска
            context_data: Начальные контекстные данные

        Returns:
            UserScenarioSession: Созданная сессия сценария
        """
        try:
            # Завершаем предыдущую активную сессию, если есть
            UserScenarioSession.objects.filter(
                bot=bot, telegram_user=telegram_user, is_active=True
            ).update(is_active=False)

            # Получаем первый шаг сценария
            first_step = scenario.get_first_step()
            if not first_step:
                raise ValueError(f"Сценарий {scenario.name} не содержит активных шагов")

            # Создаем новую сессию
            session = UserScenarioSession.objects.create(
                bot=bot,
                telegram_user=telegram_user,
                scenario=scenario,
                current_step=first_step,
                context_data=context_data or {},
            )

            logger.info(
                f"Запущен сценарий {scenario.name} для пользователя {telegram_user.telegram_id}"
            )
            return session

        except Exception as e:
            logger.error(f"Ошибка при запуске сценария: {e}")
            raise

    def get_user_session(
        self, bot: Bot, telegram_user: TelegramUser
    ) -> Optional[UserScenarioSession]:
        """
        Получить активную сессию пользователя

        Args:
            bot: Экземпляр бота
            telegram_user: Пользователь Telegram

        Returns:
            UserScenarioSession или None
        """
        try:
            return UserScenarioSession.objects.get(
                bot=bot, telegram_user=telegram_user, is_active=True
            )
        except UserScenarioSession.DoesNotExist:
            return None

    def process_user_message(
        self, session: UserScenarioSession, user_message: str
    ) -> Tuple[str, bool]:
        """
        Обработать сообщение пользователя в контексте сценария

        Args:
            session: Активная сессия сценария
            user_message: Сообщение пользователя

        Returns:
            Tuple[str, bool]: (ответ бота, завершен ли сценарий)
        """
        try:
            # Обновляем контекст с сообщением пользователя
            session.context_data["last_user_message"] = user_message
            session.context_data["user_name"] = (
                session.telegram_user.first_name or "Пользователь"
            )

            # Обрабатываем текущий шаг
            response, is_finished = self._process_step(
                session, session.current_step, user_message
            )

            if is_finished:
                session.end_session()
                logger.info(
                    f"Сценарий завершен для пользователя {session.telegram_user.telegram_id}"
                )

            return response, is_finished

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения в сценарии: {e}")
            return "Произошла ошибка при обработке сообщения", True

    def _process_step(
        self, session: UserScenarioSession, step: Step, user_message: str
    ) -> Tuple[str, bool]:
        """
        Обработать конкретный шаг сценария

        Args:
            session: Сессия сценария
            step: Текущий шаг
            user_message: Сообщение пользователя

        Returns:
            Tuple[str, bool]: (ответ, завершен ли сценарий)
        """
        step_type = step.step_type

        if step_type == "end":
            return "Сценарий завершен. Спасибо за общение!", True

        elif step_type == "gpt_request":
            return self._process_gpt_request(session, step, user_message)

        elif step_type == "message":
            return self._process_message(session, step, user_message)

        elif step_type == "input":
            return self._process_input(session, step, user_message)

        else:
            logger.warning(f"Неизвестный тип шага: {step_type}")
            # Переходим к следующему шагу
            next_step = step.get_next_step()
            if next_step:
                session.update_step(next_step)
                return self._process_step(session, next_step, user_message)
            else:
                return "Сценарий завершен", True

    def _process_gpt_request(
        self, session: UserScenarioSession, step: Step, user_message: str
    ) -> Tuple[str, bool]:
        """
        Обработать шаг с запросом к GPT

        Args:
            session: Сессия сценария
            step: Текущий шаг
            user_message: Сообщение пользователя

        Returns:
            Tuple[str, bool]: (ответ GPT, завершен ли сценарий)
        """
        try:
            # Получаем промпт и подставляем переменные
            prompt = step.data.get("prompt", "")
            formatted_prompt = self._format_prompt(prompt, session.context_data)

            # Отправляем запрос к GPT
            gpt_response = self.gpt_service.get_response(
                bot=session.bot,
                messages=[{"role": "user", "content": formatted_prompt}],
            )

            # Обрабатываем переходы
            next_step = step.process_transitions(user_message, session.context_data)

            if next_step:
                session.update_step(next_step)
                return gpt_response, False
            else:
                # Если нет переходов, завершаем сценарий
                return gpt_response, True

        except Exception as e:
            logger.error(f"Ошибка при запросе к GPT: {e}")
            return "Извините, произошла ошибка при обработке запроса", True

    def _process_message(
        self, session: UserScenarioSession, step: Step, user_message: str
    ) -> Tuple[str, bool]:
        """
        Обработать шаг с отправкой сообщения

        Args:
            session: Сессия сценария
            step: Текущий шаг
            user_message: Сообщение пользователя

        Returns:
            Tuple[str, bool]: (сообщение, завершен ли сценарий)
        """
        # Получаем текст сообщения
        message_text = step.data.get("text", "Сообщение не настроено")
        formatted_message = self._format_prompt(message_text, session.context_data)

        # Обрабатываем переходы
        next_step = step.process_transitions(user_message, session.context_data)

        if next_step:
            session.update_step(next_step)
            return formatted_message, False
        else:
            return formatted_message, True

    def _process_input(
        self, session: UserScenarioSession, step: Step, user_message: str
    ) -> Tuple[str, bool]:
        """
        Обработать шаг ожидания ввода пользователя

        Args:
            session: Сессия сценария
            step: Текущий шаг
            user_message: Сообщение пользователя

        Returns:
            Tuple[str, bool]: (ответ, завершен ли сценарий)
        """
        # Сохраняем ввод пользователя в контекст
        input_key = step.data.get("save_as", "user_input")
        session.context_data[input_key] = user_message

        # Получаем ответное сообщение
        response_message = step.data.get("response", "Спасибо за ответ!")
        formatted_response = self._format_prompt(response_message, session.context_data)

        # Обрабатываем переходы
        next_step = step.process_transitions(user_message, session.context_data)

        if next_step:
            session.update_step(next_step, {"last_input": user_message})
            return formatted_response, False
        else:
            return formatted_response, True

    def _format_prompt(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Форматировать промпт, подставляя переменные из контекста

        Args:
            prompt: Шаблон промпта
            context: Контекстные данные

        Returns:
            str: Отформатированный промпт
        """
        try:
            return prompt.format(**context)
        except KeyError as e:
            logger.warning(f"Переменная {e} не найдена в контексте")
            return prompt
        except Exception as e:
            logger.error(f"Ошибка при форматировании промпта: {e}")
            return prompt

    def end_user_scenario(self, bot: Bot, telegram_user: TelegramUser) -> bool:
        """
        Завершить активный сценарий пользователя

        Args:
            bot: Экземпляр бота
            telegram_user: Пользователь Telegram

        Returns:
            bool: True если сценарий был завершен
        """
        try:
            session = self.get_user_session(bot, telegram_user)
            if session:
                session.end_session()
                logger.info(
                    f"Сценарий принудительно завершен для пользователя {telegram_user.telegram_id}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при завершении сценария: {e}")
            return False
