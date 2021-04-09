TOKEN = '1684713538:AAG5bcA1tKJd5jamAAVq9S1lDm4kva0ZJWI'

INTENTS = [
    {
        'name': "Приветствие",
        'tokens': "Разместить новость",
        'scenario': "new_news",
        'answer': None
    },
]

SCENARIOS = {
    'new_news': {
        'first_step': 'step1',
        'steps': {
            'step1':
                {
                    'text': 'Введите название проекта\nПример: CASPER',
                    'failure_text': "Такое название уже существует! Повторите попытку!",
                    'handler': 'project_name_handler',
                    'next_step': 'step2'
                },
            'step2':
                {
                    'text': 'Проект - {name}.\nТеперь сделайте описание проекта:',
                    'failure_text': None,
                    'handler': 'project_description_handler',
                    'next_step': 'step3'
                },
            'step3':
                {
                    'text': 'Описание - {description}.\nВыберите тему проекта:',
                    'failure_text': None,
                    'handler': 'project_theme_handler',
                    'next_step': 'step4'
                },
            'step4':
                {
                    'text': 'Тема - {theme}.\n Теперь укажите дату участия\nПример: 03.04.2021',
                    'failure_text': 'Вы ввели неверный формат даты! Повторите попытку!',
                    'handler': 'project_date_handle',
                    'next_step': 'step5'
                },
            'step5':
                {
                    'text': 'Записал. Теперь укажите время\nПример: 20:21',
                    'failure_text': 'Вы ввели неверный формат времени! Повторите попытку!',
                    'handler': 'project_time_handle',
                    'next_step': 'step6'
                },
            'step6':
                {
                    'text': 'Ок, нужно ли вам напоминание?',
                    'failure_text': None,
                    'handler': 'project_reminder_handle',
                    'next_step': 'step7'
                },
            'step7':
                {
                    'text': 'Понял. Нужна ли кнопка "Следить за результатами?',
                    'failure_text': None,
                    'handler': 'project_follow_handle',
                    'next_step': 'step8'
                },
            'step8':
                {
                    'text': '{name}\n{date_participation}\n{description}',
                    'failure_text': None,
                    'handler': None,
                    'next_step': None
                },
        }
    },
}
