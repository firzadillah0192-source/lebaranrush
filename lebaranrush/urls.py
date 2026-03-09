from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('games/undercover/', include('games.undercover.urls')),
    path('games/spinwheel/', include('games.spinwheel.urls')),
    path('', include('rooms.urls')),
]
