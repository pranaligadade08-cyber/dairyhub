from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('milk_app.urls')),
]

# Serve media files in development; in production use a cloud bucket or whitenoise
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
