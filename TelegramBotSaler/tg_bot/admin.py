# from admin_interface.admin import ThemeAdmin
# from admin_interface.models import Theme
from django.contrib import admin

# Register your models here.
from tg_bot.models import TokenSale, Users, Themes, QuestionSuggestions, ReminderUsers


class TokenAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    list_filter = ['theme']


class UsersAdmin(admin.ModelAdmin):
    list_display = ['nickname', 'user_id', 'is_moderator']
    readonly_fields = ['user_id', 'notified']
    search_fields = ['user_id', 'nickname']
    list_filter = ['is_moderator']
    actions = ['mark_as_moderator', 'mark_as_user']

    def mark_as_moderator(self, request, queryset):
        queryset.update(is_moderator=True)

    def mark_as_user(self, request, queryset):
        queryset.update(is_moderator=False)

    mark_as_moderator.short_description = 'Перевести в статус модератора'
    mark_as_user.short_description = 'Перевести в статус пользователя'


class ThemesAdmin(admin.ModelAdmin):
    list_display = ['name']


class QuestionAdmin(admin.ModelAdmin):
    list_display = ['user', 'message']
    list_filter = ['user']


class ReminderUsersAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_sale', 'twelve', 'one']
    list_filter = ['user']


# admin.site.register(TokenSale, TokenAdmin)
# admin.site.register(Users, UsersAdmin)
# admin.site.register(Themes, ThemesAdmin)
# admin.site.register(QuestionSuggestions, QuestionAdmin)
# admin.site.register(ReminderUsers, ReminderUsersAdmin)
# admin.site.register(Theme, ThemeAdmin)
