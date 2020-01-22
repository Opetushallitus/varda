from django.urls import re_path
from rest_framework_swagger.views import get_swagger_view

from . import views

schema_view = get_swagger_view(title='VARDA REST API')


urlpatterns = [
    re_path(r'^$', views.varda_index, name='varda_index'),
    re_path(r'^release-notes/', views.varda_release_notes, name='varda_release_notes'),
    re_path(r'^swagger/', schema_view),
]
