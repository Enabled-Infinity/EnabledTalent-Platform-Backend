from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/organization/', include('organization.urls')),
    path('api/channels/', include('main.urls')),
    path('api/candidates/', include('candidates.urls')),
    path('api/auth/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),

]