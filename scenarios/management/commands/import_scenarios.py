import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from scenarios.models import Scenario, Step
from bots.models import Bot


class Command(BaseCommand):
    help = "Импорт примеров сценариев из JSON файла"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="example_scenarios.json",
            help="Путь к JSON файлу с примерами сценариев",
        )
        parser.add_argument(
            "--bot-id",
            type=int,
            help="ID бота для привязки сценариев (если не указан, будет использован первый доступный)",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Перезаписать существующие сценарии с такими же названиями",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        bot_id = options["bot_id"]
        overwrite = options["overwrite"]

        # Проверяем существование файла
        if not os.path.isabs(file_path):
            file_path = os.path.join(settings.BASE_DIR, file_path)

        if not os.path.exists(file_path):
            raise CommandError(f"Файл {file_path} не найден")

        # Получаем бота
        if bot_id:
            try:
                bot = Bot.objects.get(id=bot_id)
            except Bot.DoesNotExist:
                raise CommandError(f"Бот с ID {bot_id} не найден")
        else:
            bot = Bot.objects.filter(is_active=True).first()
            if not bot:
                raise CommandError(
                    "Не найдено активных ботов. Создайте бота или укажите --bot-id"
                )

        self.stdout.write(f"Используется бот: {bot.name} (ID: {bot.id})")

        # Загружаем JSON файл
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                scenarios_data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"Ошибка при чтении JSON файла: {e}")
        except Exception as e:
            raise CommandError(f"Ошибка при открытии файла: {e}")

        # Импортируем сценарии
        imported_count = 0
        skipped_count = 0

        for scenario_key, scenario_data in scenarios_data.items():
            scenario_name = scenario_data.get("name", scenario_key)

            # Проверяем существование сценария
            existing_scenario = Scenario.objects.filter(
                name=scenario_name, bot=bot
            ).first()

            if existing_scenario and not overwrite:
                self.stdout.write(
                    self.style.WARNING(
                        f'Сценарий "{scenario_name}" уже существует. Пропускаем.'
                    )
                )
                skipped_count += 1
                continue

            if existing_scenario and overwrite:
                # Удаляем существующие шаги
                existing_scenario.steps.all().delete()
                scenario = existing_scenario
                self.stdout.write(f'Перезаписываем сценарий "{scenario_name}"')
            else:
                # Создаем новый сценарий
                scenario = Scenario.objects.create(
                    name=scenario_name,
                    description=scenario_data.get("description", ""),
                    bot=bot,
                    data=scenario_data.get("data", {}),
                    is_active=True,
                )
                self.stdout.write(f'Создан сценарий "{scenario_name}"')

            # Создаем шаги
            steps_data = scenario_data.get("steps", [])
            created_steps = 0

            for step_data in steps_data:
                try:
                    step = Step.objects.create(
                        scenario=scenario,
                        name=step_data.get("name", f'Шаг {step_data.get("order", 1)}'),
                        step_type=step_data.get("step_type", "message"),
                        data=step_data.get("data", {}),
                        order=step_data.get("order", 1),
                        is_active=step_data.get("is_active", True),
                    )
                    created_steps += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Ошибка при создании шага: {e}")
                    )

            self.stdout.write(f"  Создано шагов: {created_steps}")
            imported_count += 1

        # Выводим итоги
        self.stdout.write(
            self.style.SUCCESS(
                f"\nИмпорт завершен:\n"
                f"- Импортировано сценариев: {imported_count}\n"
                f"- Пропущено сценариев: {skipped_count}\n"
                f"- Использован бот: {bot.name}"
            )
        )

        if imported_count > 0:
            self.stdout.write(
                "\nВы можете просмотреть и отредактировать импортированные сценарии "
                "в административном интерфейсе Django."
            )
