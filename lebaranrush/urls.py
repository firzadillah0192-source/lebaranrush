from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('games/undercover/', include('games.undercover.urls')),
    path('games/spinwheel/', include('games.spinwheel.urls')),
    path('', include('rooms.urls')),
]

urlpatterns += staticfiles_urlpatterns()

