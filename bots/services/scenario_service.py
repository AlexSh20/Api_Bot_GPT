import json
import logging
from typing import Dict, Any, Optional, Tuple
from django.utils import timezone
from ..models import Scenario, UserScenarioSession, Bot, TelegramUser
from .gpt_service import GPTService

logger = logging.getLogger(__name__)


class ScenarioService:
    """Сервис для работы со сценариями взаимодействия"""

    def __init__(self):
        self.gpt_service = GPTService()

    def start_scenario(
        self,
        bot: Bot,
        telegram_user: TelegramUser,
        scenario_id: str,
        context_data: Dict[str, Any] = None,
    ) -> UserScenarioSession:
        """
        Запустить сценарий для пользователя

        Args:
            bot: Экземпляр бота
            telegram_user: Пользователь Telegram
            scenario_id: ID сценария
            context_data: Начальные контекстные данные

        Returns:
            UserScenarioSession: Созданная сессия сценария
        """
        try:
            # Получаем сценарий
            scenario = Scenario.objects.get(scenario_id=scenario_id, is_active=True)

            # Завершаем предыдущую активную сессию, если есть
            UserScenarioSession.objects.filter(
                bot=bot, telegram_user=telegram_user, is_active=True
            ).update(is_active=False)

            # Создаем новую сессию
            session = UserScenarioSession.objects.create(
                bot=bot,
                telegram_user=telegram_user,
                scenario=scenario,
                current_state=scenario.get_initial_state(),
                context_data=context_data or {},
            )

            logger.info(
                f"Запущен сценарий {scenario_id} для пользователя {telegram_user.telegram_id}"
            )
            return session

        except Scenario.DoesNotExist:
            logger.error(f"Сценарий {scenario_id} не найден")
            raise ValueError(f"Сценарий {scenario_id} не найден")

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
            # Получаем текущее состояние
            current_state_data = session.scenario.get_state(session.current_state)

            if not current_state_data:
                logger.error(f"Состояние {session.current_state} не найдено в сценарии")
                return "Произошла ошибка в сценарии", True

            # Обновляем контекст с сообщением пользователя
            session.context_data["last_user_message"] = user_message
            session.context_data["user_name"] = (
                session.telegram_user.first_name or "Пользователь"
            )

            # Обрабатываем состояние
            response, is_finished = self._process_state(
                session, current_state_data, user_message
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

    def _process_state(
        self,
        session: UserScenarioSession,
        state_data: Dict[str, Any],
        user_message: str,
    ) -> Tuple[str, bool]:
        """
        Обработать конкретное состояние сценария

        Args:
            session: Сессия сценария
            state_data: Данные состояния
            user_message: Сообщение пользователя

        Returns:
            Tuple[str, bool]: (ответ, завершен ли сценарий)
        """
        state_type = state_data.get("type")

        if state_type == "end":
            return "Сценарий завершен. Спасибо за общение!", True

        elif state_type == "gpt_request":
            return self._process_gpt_request(session, state_data, user_message)

        elif state_type == "user_input":
            return self._process_user_input(session, state_data, user_message)

        else:
            logger.error(f"Неизвестный тип состояния: {state_type}")
            return "Произошла ошибка в сценарии", True

    def _process_gpt_request(
        self,
        session: UserScenarioSession,
        state_data: Dict[str, Any],
        user_message: str,
    ) -> Tuple[str, bool]:
        """
        Обработать состояние с запросом к GPT

        Args:
            session: Сессия сценария
            state_data: Данные состояния
            user_message: Сообщение пользователя

        Returns:
            Tuple[str, bool]: (ответ GPT, завершен ли сценарий)
        """
        try:
            # Получаем промпт и подставляем переменные
            prompt = state_data.get("prompt", "")
            formatted_prompt = self._format_prompt(prompt, session.context_data)

            # Отправляем запрос к GPT
            gpt_response = self.gpt_service.get_response(
                bot=session.bot,
                messages=[{"role": "user", "content": formatted_prompt}],
            )

            # Обрабатываем переходы
            next_state = self._get_next_state(
                state_data, user_message, session.context_data
            )

            if next_state:
                session.update_state(next_state)
                return gpt_response, False
            else:
                # Если нет переходов, завершаем сценарий
                return gpt_response, True

        except Exception as e:
            logger.error(f"Ошибка при запросе к GPT: {e}")
            return "Извините, произошла ошибка при обработке запроса", True

    def _process_user_input(
        self,
        session: UserScenarioSession,
        state_data: Dict[str, Any],
        user_message: str,
    ) -> Tuple[str, bool]:
        """
        Обработать состояние ожидания ввода пользователя

        Args:
            session: Сессия сценария
            state_data: Данные состояния
            user_message: Сообщение пользователя

        Returns:
            Tuple[str, bool]: (ответ, завершен ли сценарий)
        """
        # Сохраняем ввод пользователя в контекст
        input_key = state_data.get("save_as", "user_input")
        session.context_data[input_key] = user_message

        # Получаем ответное сообщение
        response_message = state_data.get("response", "Спасибо за ответ!")
        formatted_response = self._format_prompt(response_message, session.context_data)

        # Обрабатываем переходы
        next_state = self._get_next_state(
            state_data, user_message, session.context_data
        )

        if next_state:
            session.update_state(next_state)
            return formatted_response, False
        else:
            return formatted_response, True

    def _get_next_state(
        self, state_data: Dict[str, Any], user_message: str, context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Определить следующее состояние на основе переходов

        Args:
            state_data: Данные текущего состояния
            user_message: Сообщение пользователя
            context: Контекстные данные

        Returns:
            str или None: ID следующего состояния
        """
        transitions = state_data.get("transitions", [])

        for transition in transitions:
            condition = transition.get("condition")

            if condition == "always":
                return transition.get("next_state")

            elif condition == "user_responded" and user_message:
                return transition.get("next_state")

            elif condition == "keyword_match":
                keywords = transition.get("keywords", [])
                if any(keyword.lower() in user_message.lower() for keyword in keywords):
                    return transition.get("next_state")

        return None

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
