import os
from datetime import datetime
import django
from telebot import types
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TelegramBotSaler.TelegramBotSaler.settings')
django.setup()

from tg_bot.models import TokenSale, Themes


def project_name_handler(text, context, markup):
    if TokenSale.objects.filter(name=text):
        return False, None
    else:
        context['name'] = text
        return True, markup


def project_description_handler(text, context, markup):
    context['description'] = text
    for item in Themes.objects.all():
        markup.add(types.InlineKeyboardButton(text=f"{item.name}", callback_data=f"{item.name}_handle"))
    markup.add(types.InlineKeyboardButton(text='Без темы', callback_data='non_theme_handle'))
    return True, markup


def project_theme_handler(text, context, markup):
    return True, markup


def project_date_handle(text, context, markup):
    date = int(text.split('.')[0])
    month = int(text.split('.')[1])
    if re.match(r'\d\d[.]\d\d[.]\d\d\d\d', text):
        if 32 >= date > 0 < month <= 12:
            if datetime.strptime(text, '%d.%m.%Y') >= datetime.today():
                context['date_participation'] = text
                return True, markup
            else:
                return False, None
        else:
            return False, None
    else:
        return False, None


def project_time_handle(text, context, markup):
    if re.match(r'\d\d[:]\d\d', text):
        if int(text.split(':')[0]) <= 23 and int(text.split(':')[1]) <= 59:
            date_time = context['date_participation'] + ' ' + text
            context['date_participation'] = date_time
            markup.add(types.InlineKeyboardButton(text=f"Да", callback_data=f"yes_reminder"))
            markup.add(types.InlineKeyboardButton(text=f"Нет", callback_data=f"no_reminder"))
            return True, markup
        else:
            return False, None
    else:
        return False, None


def project_reminder_handle(text, context, markup):
    return True, markup


def project_follow_handle(text, context, markup):
    return True, markup
