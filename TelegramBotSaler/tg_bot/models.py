from django.db import models

# Create your models here.


class ModeratorState(models.Model):
    user_id = models.IntegerField(unique=True)
    scenario_name = models.CharField(max_length=20)
    step_name = models.CharField(max_length=20)
    context = models.JSONField(null=True)


class Themes(models.Model):

    class Meta:
        verbose_name_plural = 'Список тем'

    name = models.CharField(max_length=30, unique=True, verbose_name="Название темы")

    def __str__(self):
        return self.name


class TokenSale(models.Model):

    class Meta:
        verbose_name_plural = 'Список новостей'

    name = models.CharField(max_length=50, unique=True, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    is_reminder = models.BooleanField(default=True, verbose_name="Оповещать?")
    date_participation = models.DateTimeField(null=True, verbose_name="Крайняя дата регистрации")
    theme = models.ForeignKey(Themes, null=True, on_delete=models.DO_NOTHING, verbose_name="Тема")

    def __str__(self):
        return self.name


class Users(models.Model):

    class Meta:
        verbose_name_plural = 'Список пользователей'

    user_id = models.IntegerField(unique=True, verbose_name="tg_id пользователя")
    nickname = models.CharField(max_length=30, verbose_name="tg_username пользователя")
    is_moderator = models.BooleanField(default=False, verbose_name="Модератор?")
    tracked_themes = models.ManyToManyField(Themes, null=True, verbose_name="Отслеживаемые новости")
    notified = models.BooleanField(default=False, verbose_name="Оповещен ли о своих правах?")

    def __str__(self):
        return self.nickname


class ReminderUsers(models.Model):

    class Meta:
        verbose_name_plural = 'Подписки пользователей'

    user = models.ForeignKey(Users, null=True, on_delete=models.DO_NOTHING, verbose_name="Пользователь")
    token_sale = models.ForeignKey(TokenSale, null=True, on_delete=models.CASCADE, verbose_name="Оповещаемая новость")
    twelve = models.BooleanField(default=False, verbose_name="За 12 часов")
    one = models.BooleanField(default=False, verbose_name="За 1 час")

    def __str__(self):
        return f"{self.user} - {self.token_sale}"


class QuestionSuggestions(models.Model):

    class Meta:
        verbose_name_plural = 'Отзывы и предложения пользователей'

    user = models.ForeignKey(Users, null=True, on_delete=models.DO_NOTHING, verbose_name="Пользователь")
    message = models.TextField(max_length=1000, verbose_name="Сообщение")

    def trim_15(self):
        if len(self.message) > 15:
            return f"{self.message[:15]}..."
        else:
            return f"{self.message}"

    def __str__(self):
        return f'{self.user}, {self.trim_15()}'
