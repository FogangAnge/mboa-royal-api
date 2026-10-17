from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("comptes.urls")),
    path("api/restaurant/", include("restaurants.urls")),
    path("api/zones/", include("zones.urls")),
    path("api/menu/", include("menu.urls")),
    path("api/commandes/", include("commandes.urls")),
    path("api/livraisons/", include("livraisons.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)