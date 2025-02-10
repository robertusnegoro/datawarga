from rest_framework.throttling import UserRateThrottle
from django.conf import settings

class BotUserRateThrottle(UserRateThrottle):
    rate = '1000/minute'  # High rate limit for bot

    def allow_request(self, request, view):
        if request.user.username == settings.BOT_API_USER:
            return True  # No throttling for bot user
        return super().allow_request(request, view) 