"""TelegramBotSaler URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from admin_interface.admin import ThemeAdmin
from admin_interface.models import Theme
from django.urls import path

from django_otp.admin import OTPAdminSite
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin


class OTPAdmin(OTPAdminSite):
    pass


from django.contrib.auth.models import User
from django_otp.plugins.otp_totp.models import TOTPDevice
from tg_bot.models import TokenSale, Users, Themes, QuestionSuggestions, ReminderUsers
from tg_bot.admin import TokenAdmin, UsersAdmin, ThemesAdmin, QuestionAdmin, ReminderUsersAdmin

admin_site = OTPAdmin(name='OTPAdmin')
admin_site.register(User)
admin_site.register(TOTPDevice, TOTPDeviceAdmin)
admin_site.register(TokenSale, TokenAdmin)
admin_site.register(Users, UsersAdmin)
admin_site.register(Themes, ThemesAdmin)
admin_site.register(QuestionSuggestions, QuestionAdmin)
admin_site.register(ReminderUsers, ReminderUsersAdmin)
admin_site.register(Theme, ThemeAdmin)


urlpatterns = [
    path('admin/', admin_site.urls),
]
