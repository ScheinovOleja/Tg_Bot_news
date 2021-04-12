import base64
import copy
import re
import threading
import time
import telebot as tb
import handlers
import os
import django

from datetime import datetime
from telebot import types
from config import *

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TelegramBotSaler.TelegramBotSaler.settings')
django.setup()

from tg_bot.models import Users, TokenSale, ModeratorState, Themes, QuestionSuggestions, ReminderUsers


class TgBot:

    def __init__(self):
        self.bot = tb.TeleBot(token=TOKEN, num_threads=4)
        self.def_bots()
        self.message_start = None

    def async_reminder(self):
        """
        Проверка в фоне на оповещения за 1 и 12 часов
        """
        while True:
            reminder = ReminderUsers.objects.all()
            for item in reminder:
                then = item.token_sale.date_participation.replace(tzinfo=None)
                now = datetime.now().replace(tzinfo=None)
                duration = then - now
                seconds = 3600 if item.one else 43200
                if duration.total_seconds() <= seconds:
                    item.delete()
                    self.bot.send_message(
                        text=f"{'Остался 1 час' if seconds == 3600 else 'Осталось 12 часов'} до закрытия регистрации в "
                             f"{item.token_sale.name} на {item.token_sale.theme.name}",
                        chat_id=item.user.user_id)
                time.sleep(60)

    @staticmethod
    def async_clean():
        """
        Фоновая проверка на просроченные новости
        """
        while True:
            token_sale = TokenSale.objects.all()
            for item in token_sale:
                then = item.date_participation.replace(tzinfo=None)
                now = datetime.now().replace(tzinfo=None)
                duration = then - now
                if duration.total_seconds() < 0:
                    TokenSale.objects.filter(id=item.id).delete()
            time.sleep(60)

    def async_check_moderator(self):
        """
        Фоновая проверка и оповещение, если назначили модератора
        """
        markup_moder = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        while True:
            users = Users.objects.all()
            for user in users:
                if user.is_moderator and not user.notified:
                    markup_moder.add(types.KeyboardButton(text="Разместить новость"))
                    self.bot.send_message(
                        text=f"Вас назначили модератором.\nНажмите на /start чтобы обновить бота",
                        chat_id=user.user_id,
                        reply_markup=markup_moder
                    )
                    Users.objects.filter(user_id=user.user_id).update(notified=True)
                elif not user.is_moderator and user.notified:
                    self.bot.send_message(
                        text=f"С вас сняли должность модератора.\nНажмите /start, чтобы обновиться.",
                        chat_id=user.user_id,
                        reply_markup=types.ReplyKeyboardRemove()
                    )
                    Users.objects.filter(user_id=user.user_id).update(notified=False)
            time.sleep(5)

    def prepare(self):
        """
        Основной метод с запуском всего хаоса.
        """
        task_reminder = threading.Thread(target=self.async_reminder)
        task_cleaning = threading.Thread(target=self.async_clean)
        task_check = threading.Thread(target=self.async_check_moderator)
        task_bot = threading.Thread(target=self.bot.polling, kwargs={'none_stop': True, 'interval': 0})
        task_reminder.start()
        task_bot.start()
        task_cleaning.start()
        task_check.start()

    def def_bots(self):
        """
        Хранит в себе все методы бота
        """

        def log_error(f):
            """
            Обработчик ошибок
            :param f: обрабатываемая функция
            """

            def inner(*args, **kwargs):
                try:
                    return f(*args, **kwargs)
                except Exception as exc:
                    error = f'Ошибка - {exc}'
                    print(error)

            return inner

        @log_error
        def check_moderator(message):
            """
            Проверка на модератора
            """
            result, _ = Users.objects.get_or_create(
                user_id=message.chat.id,
                defaults={
                    'nickname':
                        message.chat.first_name + ' ' + message.chat.last_name
                        if not message.chat.username else message.chat.username,
                    'is_moderator': False,
                }
            )
            if result.is_moderator:
                return True
            return False

        @log_error
        @self.bot.message_handler(commands=['clear'])
        def clear(message):
            """
            Очистка истории сообщений
            """
            message_id = int(message.message_id)
            while True:
                try:
                    message_id -= 1
                    self.bot.delete_message(message.chat.id, message_id)
                except Exception:
                    continue

        @log_error
        def update_start_message(message, markup):
            """
            Обновление стартового сообщения после удаления из модераторов
            :param message: обрабатываемое сообщение
            :param markup: обрабатываемая разметка сообщения
            """
            user = Users.objects.get(user_id=message.chat.id)
            tracked_themes = user.tracked_themes.all()
            themes = Themes.objects.all()
            for theme in themes:
                if theme in tracked_themes:
                    markup.add(types.InlineKeyboardButton(text=f"✅ {theme.name}",
                                                          callback_data=f"{theme.name}_b_unfollow"))
                else:
                    markup.add(types.InlineKeyboardButton(text=f"{theme.name}",
                                                          callback_data=f"{theme.name}_b_follow"))
            markup.add(types.InlineKeyboardButton(text="Вопрос/предложение ✍🏻", callback_data="question"))
            return markup

        @log_error
        @self.bot.message_handler(commands=['start'])
        def run(message):
            """
            Стартовый метод, вызываемый при команде /start.
            """
            self.message_start = message.message_id
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            markup_key = update_start_message(message, markup_key)
            text = "Добро пожаловать в мониторинг токен сейлов.\n\n " \
                   "Все токен сейлы, которые я буду находить, буду делиться с тобой!\n\n" \
                   "Можешь выбрать темы, которые тебе интересны и будешь получать новости только по ним!"
            send_text(text_to_send=text, chat_id=message.chat.id, local_markup=markup_key)
            if check_moderator(message):
                send_text(text_to_send='Чтобы разместить новость нажмите на кнопку ниже!',
                          chat_id=message.chat.id)

        @log_error
        @self.bot.message_handler(content_types=['text'], func=lambda message: not message.from_user.is_bot)
        def scenario_moderator(message):
            """
            Обработка сценария создания новости. Доступно только модератору.
            """
            if check_moderator(message):
                state = None
                text = message.html_text
                chat_id = message.chat.id
                try:
                    state = ModeratorState.objects.get(user_id=chat_id)
                except Exception as exc:
                    print(exc)
                if state is not None:
                    continue_scenario(text=text, state=state, chat_id=chat_id)
                else:
                    for intent in INTENTS:
                        if any(token in text.lower() for token in intent['tokens']):
                            if intent['answer']:
                                self.bot.send_message(chat_id, intent['answer'])
                            else:
                                start_scenario(intent['scenario'], chat_id)
                            break
            else:
                send_text(text_to_send='Вы не являетесь модератором.', chat_id=message.chat.id)

        @log_error
        def send_text(text_to_send, chat_id, local_markup=None, photo=None):
            """
            Отправка сообщения с фотографией и без
            :param text_to_send: текст отправки
            :param chat_id: id чата, куда нужно отправлять
            :param local_markup: разметка сообщения
            :param photo: фотография, если имеется
            :return: возврат объекта сообщения
            """
            if photo is not None:
                return self.bot.send_photo(
                    chat_id=chat_id,
                    caption=text_to_send,
                    reply_markup=local_markup,
                    parse_mode="HTML",
                    photo=photo
                )
            else:
                return self.bot.send_message(
                    chat_id=chat_id,
                    text=text_to_send,
                    reply_markup=local_markup,
                    parse_mode="HTML"
                )

        @log_error
        def send_step(step, chat_id, text, context, local_markup=None):
            """
            Отправка сообщений из сценария
            :param step: шаг сценария
            :param chat_id: id чата, куда нужно отправлять
            :param text: текст отправки
            :param context: контекст отправки
            :param local_markup: разметка сообщения
            :return: возврат объекта сообщения
            """
            if text is None:
                return self.bot.send_message(chat_id=chat_id, text=step['text'].format(**context),
                                             reply_markup=local_markup, parse_mode="HTML")

        @log_error
        def get_object_scenario(message):
            """
            Метод получения объектов сценария.
            :param message: входное сообщение
            :return: Состояние сценария, шаг сценария, следующий шаг сценария
            """
            state = ModeratorState.objects.get(user_id=message.chat.id)
            steps = SCENARIOS[state.scenario_name]['steps']
            step = steps[state.step_name]
            next_step = steps[step['next_step']]
            return state, step, next_step

        @log_error
        def start_scenario(scenario_name, chat_id):
            """
            Начало сценария. Только для модераторов.
            :param scenario_name: имя сценария
            :param chat_id: id чата, куда нужно отправлять сообщения
            """
            scenario = SCENARIOS[scenario_name]
            first_step = scenario['first_step']
            step = scenario['steps'][first_step]
            send_step(step, chat_id, None, context={})
            ModeratorState.objects.create(user_id=chat_id, scenario_name=scenario_name, step_name=first_step,
                                          context={})

        @log_error
        def continue_scenario(text, state, chat_id):
            """
            Продолжения сценария. Вызывается на каждом новом шаге, не считая шагов с кнопками.
            :param text: текст модератора
            :param state: состояние модератора
            :param chat_id: id чата, куда нужно отправлять сообщения
            """
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            steps = SCENARIOS[state.scenario_name]['steps']
            step = steps[state.step_name]
            handler = getattr(handlers, step['handler'])
            check, markup_key = handler(text=text, context=state.context, markup=markup_key)
            if check:
                next_step = steps[step['next_step']]
                send_step(next_step, chat_id, None, state.context, local_markup=markup_key)
                if next_step['next_step']:
                    ModeratorState.objects.update(step_name=step['next_step'], context=state.context)
            else:
                text_to_send = step['failure_text'].format(**state.context)
                send_text(text_to_send, chat_id)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_handle" in call.data)
        def choice_theme(call):
            """
            Выбор темы новости.
            :param call: данные из нажатой кнопки
            """
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            markup_key.add(types.InlineKeyboardButton(text='Пропустить', callback_data='skip'))
            state, step, next_step = get_object_scenario(call.message)
            state.context['theme'] = call.data.split('_handle')[0]
            send_step(next_step, call.from_user.id, None, state.context, local_markup=markup_key)
            self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
            ModeratorState.objects.update(step_name=step['next_step'], context=state.context)
            self.bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: call.data == 'skip')
        def skip_step(call):
            """
            Пропустить шаг.
            """
            state, step, next_step = get_object_scenario(call.message)
            state.step_name = step['next_step']
            send_step(next_step, call.from_user.id, None, state.context)
            ModeratorState.objects.update(step_name=step['next_step'], context=state.context)
            self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_reminder" in call.data)
        def is_reminder(call):
            """
            Нужно ли ставить оповещение за 1 и 12 часов?
            """
            self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            state, step, next_step = get_object_scenario(call.message)
            if 'yes' in call.data:
                state.context['is_reminder'] = True
                markup_key.add(types.InlineKeyboardButton(text="Напомнить за 12 часов", callback_data="unuseful"))
                markup_key.add(types.InlineKeyboardButton(text="Напомнить за 1 час", callback_data="unuseful"))
            elif 'no' in call.data:
                state.context['is_reminder'] = False
            send_step(next_step, call.message.chat.id, None, state.context, local_markup=markup_key)
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            markup_key.add(types.InlineKeyboardButton(text="Разместить запись", callback_data="post_answer"))
            markup_key.add(types.InlineKeyboardButton(text="Удалить запись", callback_data="delete_answer"))
            self.bot.send_message(text='...', chat_id=call.message.chat.id, reply_markup=markup_key)
            ModeratorState.objects.update(step_name=step['next_step'], context=state.context)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_answer" in call.data)
        def post_or_delete(call):
            """
            Метод выбора: выложить или удалить новость
            """
            state = ModeratorState.objects.get(user_id=call.message.chat.id)
            state_copy = copy.copy(state)
            if 'post' in call.data:
                if state.context['theme'] == 'non_theme':
                    theme = None
                else:
                    theme = Themes.objects.get(name=state.context['theme'])
                try:
                    if state.context['image']:
                        image = state.context['image'].encode('utf-8')
                    else:
                        image = None
                except KeyError:
                    image = None
                TokenSale.objects.create(
                    name=state.context['name'],
                    description=state.context['description'],
                    is_reminder=state.context['is_reminder'],
                    date_participation=datetime.strptime(state.context['date_participation'], '%d.%m.%Y %H:%M'),
                    theme=theme,
                    image=image
                )
                self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
                ModeratorState.objects.filter(user_id=state.user_id).delete()
                send_text(
                    chat_id=call.message.chat.id,
                    text_to_send='Новость успешно размещена!',
                )
                mail_subscribers(state_copy.context)
            else:
                ModeratorState.objects.filter(user_id=state.user_id).delete()
                send_text(
                    chat_id=call.message.chat.id,
                    text_to_send='Новость успешно удалена!',
                )
            self.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            self.bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)

        @log_error
        def mail_subscribers(context):
            """
            Рассылка по всем подписанным пользователям, если выходит новая новость.
            """
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            try:
                theme = Themes.objects.get(name=context['theme'])
            except Exception:
                users = Users.objects.all()
            else:
                users = Users.objects.filter(tracked_themes=theme.id)
            new = TokenSale.objects.get(name=context['name'])
            text = f'{new.description}'
            if new.is_reminder:
                markup_key.add(types.InlineKeyboardButton(
                    text="Напомнить за 12 часов", callback_data=f"{new.id}_twelve_hours"))
                markup_key.add(types.InlineKeyboardButton(
                    text="Напомнить за 1 час", callback_data=f"{new.id}_one_hour"))
            for user in users:
                decoded = None
                if new.image:
                    decoded = base64.b64decode(new.image)
                send_text(
                    chat_id=user.user_id,
                    text_to_send=text,
                    local_markup=markup_key,
                    photo=decoded
                )

        @log_error
        @self.bot.callback_query_handler(func=lambda call: call.data == "back")
        def back(call):
            """
            Выход в главное меню
            """
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
            run(call.message)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: call.data == "question")
        def question(call):
            """
            Книга отзывов и предложений
            """
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            markup_key.add(types.InlineKeyboardButton(text='Назад в меню', callback_data='back'))
            text = 'Напишите пожалуйста, что хотите спросить или предложить'
            msg = send_text(text_to_send=text, chat_id=call.message.chat.id, local_markup=markup_key)
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
            self.bot.register_next_step_handler(msg, question_and_suggestions, msg.message_id)

        @log_error
        def question_and_suggestions(message, message_id):
            """
            Получение текста из отзыва и запись его в базу.
            """
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            self.bot.edit_message_reply_markup(message.chat.id, message_id)
            markup_key.add(types.InlineKeyboardButton(text='Назад в меню', callback_data='back'))
            text = "Спасибо, мы получили ваше сообщение и свяжемся с вами в случае необходимости"
            user = Users.objects.get(user_id=message.chat.id)
            QuestionSuggestions.objects.create(
                user=user,
                message=message.text)
            send_text(text_to_send=text, chat_id=message.chat.id, local_markup=markup_key)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_b_unfollow" in call.data)
        def unfollow_news(call):
            """
            Отписаться от новости
            """
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            theme = Themes.objects.get(name=call.data.split("_b_unfollow")[0])
            user = Users.objects.get(user_id=call.from_user.id)
            user.tracked_themes.remove(theme)
            markup_key = update_start_message(call.message, markup_key)
            self.bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                               message_id=call.message.message_id,
                                               reply_markup=markup_key)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_b_follow" in call.data)
        def follow_news(call):
            """
            Подписаться на новость
            """
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            theme = Themes.objects.get(name=call.data.split("_b_follow")[0])
            user = Users.objects.get(user_id=call.from_user.id)
            user.tracked_themes.add(theme)
            markup_key = update_start_message(call.message, markup_key)
            self.bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                               message_id=call.message.message_id,
                                               reply_markup=markup_key)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_hour" in call.data)
        def reminder(call):
            """
            Проверка нажатия на кнопку оповещения за 1 и 12 часов.
            """
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            user = Users.objects.get(user_id=call.message.chat.id)
            new = TokenSale.objects.get(id=int(re.match(r'\d*', call.data).group()))
            result, _ = ReminderUsers.objects.update_or_create(
                user_id=user.id,
                token_sale_id=new.id,
                defaults={
                    'one': True if "one" in call.data else False,
                    'twelve': True if "twelve" in call.data else False
                }
            )
            if 'twelve' in call.data:
                markup_key.add(types.InlineKeyboardButton(
                    text="✅ Напомнить за 12 часов", callback_data=f"{new.id}_twelve_hours"))
                markup_key.add(types.InlineKeyboardButton(
                    text="Напомнить за 1 час", callback_data=f"{new.id}_one_hour"))
            else:
                markup_key.add(types.InlineKeyboardButton(
                    text="Напомнить за 12 часов", callback_data=f"{new.id}_twelve_hours"))
                markup_key.add(types.InlineKeyboardButton(
                    text="✅ Напомнить за 1 час", callback_data=f"{new.id}_one_hour"))
            self.bot.edit_message_reply_markup(
                chat_id=call.from_user.id,
                message_id=call.message.message_id,
                reply_markup=markup_key
            )

        @log_error
        @self.bot.message_handler(content_types=['photo'])
        def test_image(message):
            """
            Обработка присылаемого сообщения и запись его в бинарном формате в базу.
            """
            state, step, next_step = get_object_scenario(message)
            image_info = self.bot.get_file(message.photo[-1].file_id)
            image = self.bot.download_file(image_info.file_path)
            encoded = base64.b64encode(image)
            state.context['image'] = encoded.decode('utf-8')
            send_step(next_step, message.chat.id, None, state.context)
            ModeratorState.objects.update(step_name=step['next_step'], context=state.context)
            self.bot.edit_message_reply_markup(message.chat.id, message.message_id)


if __name__ == '__main__':
    test = TgBot()
    test.prepare()
