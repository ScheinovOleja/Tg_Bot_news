from django.contrib import admin

# Register your models here.

from .models import TokenSale, Users, Themes, QuestionSuggestions, ReminderUsers


class TokenAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description']
    list_filter = ['theme']


class UsersAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'nickname', 'is_moderator']
    readonly_fields = ['id', 'user_id', 'notified']
    search_fields = ['id', 'user_id', 'nickname']
    list_filter = ['is_moderator']
    actions = ['mark_as_moderator', 'mark_as_user']

    def mark_as_moderator(self, request, queryset):
        queryset.update(is_moderator=True)

    def mark_as_user(self, request, queryset):
        queryset.update(is_moderator=False)

    mark_as_moderator.short_description = 'Перевести статус модератора'
    mark_as_user.short_description = 'Перевести статус пользователя'


class ThemeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'message']
    list_filter = ['user']


class ReminderUsersAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_sale', 'twelve', 'one']
    list_filter = ['user']


admin.site.register(TokenSale, TokenAdmin)
admin.site.register(Users, UsersAdmin)
admin.site.register(Themes, ThemeAdmin)
admin.site.register(QuestionSuggestions, QuestionAdmin)
admin.site.register(ReminderUsers, ReminderUsersAdmin)
