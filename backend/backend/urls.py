from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from courses import views as course_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', course_views.index_view, name='index'),
    path('courses/', include('courses.urls', namespace='courses')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('about/', course_views.about_view, name='about'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Кастомные страницы ошибок
handler404 = 'courses.views.error_404'
handler500 = 'courses.views.error_500'