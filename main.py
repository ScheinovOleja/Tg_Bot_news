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
        self.bot = tb.TeleBot(token=TOKEN)
        self.def_bots()

    def async_reminder(self):
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
        moderators = []
        while True:
            users = Users.objects.all()
            for user in users:
                if user not in moderators and user.is_moderator and not user.notified:
                    moderators.append(user)
                    self.bot.send_message(
                        text=f"Теперь ты модератор! Пропиши /start, чтобы обновиться",
                        chat_id=user.user_id)
                    Users.objects.filter(user_id=user.user_id).update(notified=True)
                elif user in moderators and not user.is_moderator and user.notified:
                    moderators.remove(user)
                    self.bot.send_message(
                        text=f"С тебя сняли должность модератора. Пропиши /start, чтобы обновиться",
                        chat_id=user.user_id)
                    Users.objects.filter(user_id=user.user_id).update(notified=False)
            time.sleep(5)

    def prepare(self):
        task_reminder = threading.Thread(target=self.async_reminder)
        task_cleaning = threading.Thread(target=self.async_clean)
        task_check = threading.Thread(target=self.async_check_moderator)
        task_bot = threading.Thread(target=self.bot.polling, kwargs={'none_stop': True})
        task_reminder.start()
        task_bot.start()
        task_cleaning.start()
        task_check.start()

    def def_bots(self):

        def log_error(f):
            def inner(*args, **kwargs):
                try:
                    return f(*args, **kwargs)
                except Exception as exc:
                    error = f'Ошибка - {exc}'
                    print(error)
                    raise exc

            return inner

        @log_error
        def check_moderator(message):
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
            test = int(message.message_id)
            while True:
                try:
                    test -= 1
                    self.bot.delete_message(message.chat.id, test)
                except:
                    continue

        @log_error
        @self.bot.callback_query_handler(func=lambda call: call.data == "update")
        def update(call):
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
            run(call.message)

        @log_error
        @self.bot.message_handler(commands=['start'])
        def run(message):
            user = Users.objects.get(user_id=message.chat.id)
            tracked_themes = user.tracked_themes.all()
            markup_moder = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            if not check_moderator(message):
                markup_key = types.InlineKeyboardMarkup(row_width=2)
                themes = Themes.objects.all()
                for theme in themes:
                    if theme in tracked_themes:
                        markup_key.add(types.InlineKeyboardButton(text=f"✅ {theme.name}",
                                                                  callback_data=f"{theme.name}_b_unfollow"))
                    else:
                        markup_key.add(types.InlineKeyboardButton(text=f"{theme.name}",
                                                                  callback_data=f"{theme.name}_b_follow"))
                markup_key.add(types.InlineKeyboardButton(text="Обновить список тем", callback_data="update"))
                markup_key.add(types.InlineKeyboardButton(text="Вопрос/предложение ✍🏻", callback_data="question"))
                try:
                    msg = send_text(
                        text_to_send="/",
                        chat_id=message.chat.id,
                        local_markup=types.ReplyKeyboardRemove()
                    )
                except:
                    msg = send_text(
                        text_to_send="/",
                        chat_id=message.chat.id
                    )
                self.bot.delete_message(msg.chat.id, msg.message_id)
                text = "Добро пожаловать в мониторинг токен сейлов.\n\n " \
                       "Все токен сейлы, которые я буду находить, буду делиться с тобой!\n\n" \
                       "Можешь выбрать темы, которые тебе интересны и будешь получать новости только по ним!"
                send_text(text_to_send=text, chat_id=message.chat.id, local_markup=markup_key)
            else:
                markup_moder.add(types.KeyboardButton(text="Разместить новость"))
                send_text(text_to_send='Чтобы разместить новость нажмите на кнопку ниже!',
                          chat_id=message.chat.id,
                          local_markup=markup_moder)

        @log_error
        @self.bot.message_handler(content_types=['text'])
        def scenario_moderator(message):
            if check_moderator(message):
                state = None
                text = message.text
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
                send_text(text_to_send='Ты не модер, пшел вон отсюда!', chat_id=message.chat.id)

        @log_error
        def send_text(text_to_send, chat_id, local_markup=None):
            return self.bot.send_message(
                chat_id=chat_id,
                text=text_to_send,
                reply_markup=local_markup)

        @log_error
        def send_step(step, chat_id, text, context, local_markup=None):
            if text is None:
                return self.bot.send_message(chat_id=chat_id, text=step['text'].format(**context),
                                             reply_markup=local_markup)
            else:
                return self.bot.send_message(chat_id=chat_id,
                                             text=text,
                                             reply_markup=local_markup)

        @log_error
        def get_object_scenario(call):
            state = ModeratorState.objects.get(user_id=call.message.chat.id)
            steps = SCENARIOS[state.scenario_name]['steps']
            step = steps[state.step_name]
            next_step = steps[step['next_step']]
            return state, step, next_step

        @log_error
        def start_scenario(scenario_name, chat_id):
            scenario = SCENARIOS[scenario_name]
            first_step = scenario['first_step']
            step = scenario['steps'][first_step]
            send_step(step, chat_id, None, context={})
            ModeratorState.objects.create(user_id=chat_id, scenario_name=scenario_name, step_name=first_step,
                                          context={})

        @log_error
        def continue_scenario(text, state, chat_id):
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
        def callback_scenario(call):
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            state, step, next_step = get_object_scenario(call)
            state.context['theme'] = call.data.split('_handle')[0]
            send_step(next_step, call.from_user.id, None, state.context, local_markup=markup_key)
            self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
            ModeratorState.objects.update(step_name=step['next_step'], context=state.context)
            self.bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_reminder" in call.data)
        def is_reminder(call):
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            state, step, next_step = get_object_scenario(call)
            markup_key.add(types.InlineKeyboardButton(text=f"Да", callback_data=f"yes_follow"))
            markup_key.add(types.InlineKeyboardButton(text=f"Нет", callback_data=f"no_follow"))
            if 'yes' in call.data:
                state.context['is_reminder'] = True
            elif 'no' in call.data:
                state.context['is_reminder'] = False
            send_step(next_step, call.message.chat.id, None, state.context, local_markup=markup_key)
            self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
            ModeratorState.objects.update(step_name=step['next_step'], context=state.context)
            return

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_follow" in call.data and "_b_follow" not in call.data)
        def is_follow(call):
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            state, step, next_step = get_object_scenario(call)
            if 'yes' in call.data:
                state.context['is_follow'] = True
                markup_key.add(types.InlineKeyboardButton(text="Следить за результатами", callback_data="unuseful"))
            elif 'no' in call.data:
                state.context['is_follow'] = False
            if state.context['is_reminder']:
                markup_key.add(types.InlineKeyboardButton(text="Напомнить за 12 часов", callback_data="unuseful"))
                markup_key.add(types.InlineKeyboardButton(text="Напомнить за 1 час", callback_data="unuseful"))
            send_step(next_step, call.message.chat.id, None, state.context, local_markup=markup_key)
            self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
            ModeratorState.objects.update(step_name=step['next_step'], context=state.context)
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            markup_key.add(types.InlineKeyboardButton(text="Разместить запись", callback_data="post_answer"))
            markup_key.add(types.InlineKeyboardButton(text="Удалить запись", callback_data="delete_answer"))
            send_text(text_to_send='...', chat_id=call.message.chat.id, local_markup=markup_key)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_answer" in call.data)
        def post_or_delete(call):
            state = ModeratorState.objects.get(user_id=call.message.chat.id)
            if 'post' in call.data:
                if state.context['theme'] == 'non_theme':
                    theme = None
                else:
                    theme = Themes.objects.get(name=state.context['theme'])
                TokenSale.objects.create(
                    name=state.context['name'],
                    description=state.context['description'],
                    is_reminder=state.context['is_reminder'],
                    is_follow=state.context['is_follow'],
                    date_participation=datetime.strptime(state.context['date_participation'], '%d.%m.%Y %H:%M'),
                    theme=theme,
                )
                mail_subscribers(state.context)
                self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
                self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id - 1)
                ModeratorState.objects.filter(user_id=state.user_id).delete()
            else:
                ModeratorState.objects.filter(user_id=state.user_id).delete()
            self.bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            return

        @log_error
        def mail_subscribers(context):
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            try:
                theme = Themes.objects.get(name=context['theme'])
            except Exception:
                theme = None
                users = Users.objects.all()
            else:
                users = Users.objects.filter(tracked_themes=theme.id)
            new = TokenSale.objects.get(name=context['name'])
            text = f'Новая новость!!\n\n' \
                   f'{new.name}{"" if not theme else f"на {theme.name}"}\n\n' \
                   f'Конец регистрации - {new.date_participation}\n\n' \
                   f'{new.description}'
            if new.is_reminder:
                markup_key.add(types.InlineKeyboardButton(
                    text="Напомнить за 12 часов", callback_data=f"{new.id}_twelve_hours"))
                markup_key.add(types.InlineKeyboardButton(
                    text="Напомнить за 1 часов", callback_data=f"{new.id}_one_hour"))
            if new.is_follow:
                markup_key.add(types.InlineKeyboardButton(
                    text="Следить за результатами",
                    callback_data=f"{new.theme.name}_b_follow"))
            for user in users:
                send_text(
                    chat_id=user.user_id,
                    text_to_send=text,
                    local_markup=markup_key
                )

        @log_error
        @self.bot.callback_query_handler(func=lambda call: call.data == "back")
        def back(call):
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
            run(call.message)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: call.data == "question")
        def question(call):
            markup_key = types.InlineKeyboardMarkup(row_width=2)
            markup_key.add(types.InlineKeyboardButton(text='Назад в меню', callback_data='back'))
            text = 'Напишите пожалуйста, что хотите спросить или предложить'
            msg = send_text(text_to_send=text, chat_id=call.message.chat.id, local_markup=markup_key)
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
            self.bot.register_next_step_handler(msg, question_and_suggestions, msg.message_id)

        @log_error
        def question_and_suggestions(message, message_id):
            self.bot.edit_message_reply_markup(message.chat.id, message_id)
            text = "Спасибо, мы получили ваше сообщение и свяжемся с вами в случае необходимости"
            user = Users.objects.get(user_id=message.chat.id)
            QuestionSuggestions.objects.create(
                user=user,
                message=message.text)
            msg = send_text(text_to_send=text, chat_id=message.chat.id)
            self.bot.edit_message_reply_markup(message.chat.id, msg.message_id)
            run(message)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_b_unfollow" in call.data)
        def follow_news(call):
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
            theme = Themes.objects.get(name=call.data.split("_b_unfollow")[0])
            user = Users.objects.get(user_id=call.from_user.id)
            user.tracked_themes.remove(theme)
            run(call.message)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_b_follow" in call.data)
        def follow_news(call):
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
            theme = Themes.objects.get(name=call.data.split("_b_follow")[0])
            user = Users.objects.get(user_id=call.from_user.id)
            user.tracked_themes.add(theme)
            run(call.message)

        @log_error
        @self.bot.callback_query_handler(func=lambda call: "_hour" in call.data)
        def reminder_twelve(call):
            user = Users.objects.get(user_id=call.message.chat.id)
            new = TokenSale.objects.get(id=int(re.match(r'\d*', call.data).group()))
            result, _ = ReminderUsers.objects.get_or_create(
                user_id=user.id,
                token_sale_id=new.id,
                defaults={
                    'one': True if "one" in call.data else False,
                    'twelve': True if "twelve" in call.data else False
                }
            )
            send_text(
                text_to_send=f'Мы обязательно оповестим вас за '
                             f'{"1 час" if "one" in call.data else "12 часов"} до начала!!',
                chat_id=call.from_user.id)
            self.bot.edit_message_reply_markup(
                call.from_user.id,
                call.message.message_id,
            )


if __name__ == '__main__':
    test = TgBot()
    test.prepare()
