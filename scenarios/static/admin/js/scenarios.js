// JavaScript для улучшения функциональности админки сценариев

(function ($) {
    'use strict';

    // Шаблоны данных для разных типов шагов
    const STEP_TEMPLATES = {
        'message': {
            'text': 'Введите текст сообщения',
            'transitions': [
                {
                    'condition': 'always',
                    'next_step_order': null
                }
            ]
        },
        'gpt_request': {
            'prompt': 'Введите промпт для GPT. Доступные переменные: {user_name}, {last_user_message}',
            'transitions': [
                {
                    'condition': 'user_responded',
                    'next_step_order': null
                }
            ]
        },
        'input': {
            'text': 'Что вы хотите ввести?',
            'save_as': 'user_input',
            'response': 'Спасибо за ввод: {user_input}',
            'transitions': [
                {
                    'condition': 'user_responded',
                    'next_step_order': null
                }
            ]
        },
        'condition': {
            'conditions': [
                {
                    'field': 'user_input',
                    'operator': 'equals',
                    'value': 'да',
                    'next_step_order': null
                }
            ]
        },
        'end': {
            'message': 'Сценарий завершен. Спасибо!'
        }
    };

    // Функция для обновления данных шага при изменении типа
    window.updateStepData = function (stepType) {
        const dataField = document.getElementById('id_data');
        if (dataField && STEP_TEMPLATES[stepType]) {
            // Проверяем, пустое ли поле или содержит шаблон
            const currentValue = dataField.value.trim();
            if (!currentValue || isTemplateData(currentValue)) {
                const template = JSON.stringify(STEP_TEMPLATES[stepType], null, 2);
                dataField.value = template;

                // Показываем уведомление
                showNotification('Данные шага обновлены согласно выбранному типу', 'success');
            }
        }
    };

    // Проверка, является ли текущее значение шаблоном
    function isTemplateData(value) {
        try {
            const parsed = JSON.parse(value);
            // Проверяем, содержит ли значение типичные шаблонные фразы
            const jsonString = JSON.stringify(parsed);
            return jsonString.includes('Введите') ||
                jsonString.includes('Доступные переменные') ||
                jsonString.includes('Что вы хотите');
        } catch (e) {
            return false;
        }
    }

    // Функция для показа уведомлений
    function showNotification(message, type = 'info') {
        const notification = $('<div class="notification-message">')
            .addClass('notification-' + type)
            .text(message)
            .css({
                'position': 'fixed',
                'top': '20px',
                'right': '20px',
                'background': type === 'success' ? '#00b894' : '#74b9ff',
                'color': 'white',
                'padding': '10px 15px',
                'border-radius': '4px',
                'z-index': '9999',
                'box-shadow': '0 2px 10px rgba(0,0,0,0.1)'
            });

        $('body').append(notification);

        // Автоматически скрываем через 3 секунды
        setTimeout(function () {
            notification.fadeOut(300, function () {
                $(this).remove();
            });
        }, 3000);
    }

    // Функция для форматирования JSON
    function formatJSON(textarea) {
        try {
            const parsed = JSON.parse(textarea.value);
            textarea.value = JSON.stringify(parsed, null, 2);
            showNotification('JSON отформатирован', 'success');
        } catch (e) {
            showNotification('Ошибка в JSON: ' + e.message, 'error');
        }
    }

    // Инициализация при загрузке страницы
    $(document).ready(function () {

        // Добавляем кнопку форматирования JSON для полей данных
        $('textarea[id$="_data"]').each(function () {
            const textarea = this;
            const $textarea = $(textarea);

            // Создаем кнопку форматирования
            const $formatBtn = $('<button type="button" class="button">Форматировать JSON</button>')
                .css({
                    'margin-left': '10px',
                    'margin-top': '5px'
                })
                .click(function (e) {
                    e.preventDefault();
                    formatJSON(textarea);
                });

            // Добавляем кнопку после textarea
            $textarea.after($formatBtn);
        });

        // Автоматическое обновление порядка шагов при изменении сценария
        $('#id_scenario').change(function () {
            const scenarioId = $(this).val();
            if (scenarioId && !$('#id_order').val()) {
                // Получаем следующий порядковый номер через AJAX
                $.get('/admin/scenarios/step/', {
                    scenario_id: scenarioId,
                    format: 'json'
                }).done(function (data) {
                    if (data && data.length > 0) {
                        const maxOrder = Math.max(...data.map(step => step.order || 0));
                        $('#id_order').val(maxOrder + 1);
                    } else {
                        $('#id_order').val(1);
                    }
                });
            }
        });

        // Подсветка синтаксиса для JSON полей (простая)
        $('textarea[id$="_data"]').on('input', function () {
            const $this = $(this);
            try {
                JSON.parse($this.val());
                $this.css('border-color', '#00b894');
            } catch (e) {
                if ($this.val().trim()) {
                    $this.css('border-color', '#e17055');
                } else {
                    $this.css('border-color', '');
                }
            }
        });

        // Добавляем подсказки для полей
        const helpTexts = {
            'id_step_type': 'Выберите тип шага. Данные будут автоматически заполнены шаблоном.',
            'id_order': 'Порядковый номер выполнения шага в сценарии.',
            'id_data': 'JSON данные конфигурации шага. Используйте кнопку "Форматировать JSON" для улучшения читаемости.'
        };

        Object.keys(helpTexts).forEach(function (fieldId) {
            const $field = $('#' + fieldId);
            if ($field.length && !$field.siblings('.help').length) {
                $field.after('<div class="help">' + helpTexts[fieldId] + '</div>');
            }
        });

        // Улучшение работы с inline формами
        $('.inline-group').each(function () {
            const $inlineGroup = $(this);

            // Добавляем кнопки быстрого создания шагов
            const $quickActions = $('<div class="inline-quick-actions">')
                .css({
                    'margin': '10px 0',
                    'padding': '10px',
                    'background': '#f8f9fa',
                    'border-radius': '4px'
                })
                .html(`
                    <strong>Быстрое создание:</strong>
                    <button type="button" class="button quick-message">Сообщение</button>
                    <button type="button" class="button quick-gpt">GPT запрос</button>
                    <button type="button" class="button quick-input">Ввод данных</button>
                    <button type="button" class="button quick-end">Завершение</button>
                `);

            $inlineGroup.find('.add-row').before($quickActions);

            // Обработчики для быстрого создания
            $quickActions.find('.quick-message').click(function () {
                addQuickStep($inlineGroup, 'message', 'Новое сообщение');
            });

            $quickActions.find('.quick-gpt').click(function () {
                addQuickStep($inlineGroup, 'gpt_request', 'GPT запрос');
            });

            $quickActions.find('.quick-input').click(function () {
                addQuickStep($inlineGroup, 'input', 'Ввод данных');
            });

            $quickActions.find('.quick-end').click(function () {
                addQuickStep($inlineGroup, 'end', 'Завершение сценария');
            });
        });
    });

    // Функция для быстрого добавления шага
    function addQuickStep(inlineGroup, stepType, stepName) {
        // Находим кнопку добавления строки и кликаем по ней
        const addButton = inlineGroup.find('.add-row a')[0];
        if (addButton) {
            addButton.click();

            // Ждем появления новой строки и заполняем её
            setTimeout(function () {
                const newRow = inlineGroup.find('.dynamic-form:last');
                newRow.find('input[id$="-name"]').val(stepName);
                newRow.find('select[id$="-step_type"]').val(stepType);

                // Устанавливаем порядок
                const orderField = newRow.find('input[id$="-order"]');
                if (!orderField.val()) {
                    const maxOrder = Math.max(...inlineGroup.find('input[id$="-order"]')
                        .map(function () { return parseInt($(this).val()) || 0; }).get());
                    orderField.val(maxOrder + 1);
                }

                showNotification(`Добавлен шаг "${stepName}"`, 'success');
            }, 100);
        }
    }

})(django.jQuery);