from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.http import HttpResponse
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('sitemap.xml', TemplateView.as_view(template_name="sitemap.xml", content_type="application/xml")),
    path('google886842ad110356f8.html', TemplateView.as_view(template_name="google886842ad110356f8.html", content_type="text/html")),
    path('', include('core.urls')),
    path('games/undercover/', include('games.undercover.urls')),
    path('games/spinwheel/', include('games.spinwheel.urls')),
    path('', include('rooms.urls')),
]

from django.conf.urls.static import static

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

