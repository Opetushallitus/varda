from django.urls import re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from . import views


schema_view = get_schema_view(
    openapi.Info(
        title='VARDA REST API',
        default_version='v1',
    ),
    public=False,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    re_path(r'^$', views.varda_index, name='varda_index'),
    re_path(r'^release-notes/', views.varda_release_notes, name='varda_release_notes'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
