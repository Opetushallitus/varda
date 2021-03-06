"""webapps URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/dev/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import re

import django_cas_ng.views as django_cas_ng_views
from django.apps import apps
from django.conf import settings

from django.contrib import admin
from django.urls import include, re_path
from django.views.decorators.clickjacking import xframe_options_exempt, xframe_options_sameorigin
from django_spaghetti.views import Plate
from drf_yasg import openapi
from drf_yasg.views import get_schema_view as get_schema_view_yasg
from rest_framework import routers, permissions
from rest_framework.renderers import CoreJSONRenderer
from rest_framework.schemas import get_schema_view
from rest_framework_nested import routers as nested_routers

from varda import (views, viewsets, viewsets_reporting, viewsets_ui, viewsets_oppija, viewsets_henkilosto,
                   viewsets_julkinen)
from varda.cas.oppija_cas_views import OppijaCasLoginView
from varda.misc_viewsets import PublicSwaggerRenderer, PublicSchemaGenerator


schema_view = get_schema_view(title='VARDA API', renderer_classes=[CoreJSONRenderer])
router_admin = routers.DefaultRouter()
router_admin.register(r'users', viewsets.UserViewSet)
router_admin.register(r'groups', viewsets.GroupViewSet)
router_admin.register(r'update-henkilo', viewsets.UpdateHenkiloWithOid, basename='update-henkilo')
router_admin.register(r'update-oph-staff', viewsets.UpdateOphStaff, basename='update-oph-staff')
router_admin.register(r'huoltajat', viewsets.HuoltajaViewSet)
router_admin.register(r'huoltajuussuhteet', viewsets.HuoltajuussuhdeViewSet)
router_admin.register(r'clear-cache', viewsets.ClearCacheViewSet, basename='clear-cache')
router_admin.register(r'hae-yksiloimattomat', viewsets.HaeYksiloimattomatHenkilotViewSet, basename='hae-yksiloimattomat')

router_user = routers.DefaultRouter()
router_user.register(r'data', viewsets.ActiveUserViewSet)
router_user.register(r'apikey', viewsets.ApikeyViewSet)

router_pulssi = routers.DefaultRouter()
router_pulssi.register(r'vakajarjestajat', viewsets.PulssiVakajarjestajat, basename='hae-vakajarjestajat')

router_ui = routers.DefaultRouter()
router_ui.register(r'vakajarjestajat', viewsets_ui.UiVakajarjestajatViewSet, basename='hae-vakajarjestajat')

router = routers.DefaultRouter()
router.register(r'vakajarjestajat', viewsets.VakaJarjestajaViewSet)
router.register(r'toimipaikat', viewsets.ToimipaikkaViewSet)
router.register(r'toiminnallisetpainotukset', viewsets.ToiminnallinenPainotusViewSet)
router.register(r'kielipainotukset', viewsets.KieliPainotusViewSet)
router.register(r'hae-henkilo', viewsets.HaeHenkiloViewSet, 'hae-henkilo')
router.register(r'henkilot', viewsets.HenkiloViewSet)
router.register(r'lapset', viewsets.LapsiViewSet)
router.register(r'maksutiedot', viewsets.MaksutietoViewSet)
router.register(r'varhaiskasvatuspaatokset', viewsets.VarhaiskasvatuspaatosViewSet)
router.register(r'varhaiskasvatussuhteet', viewsets.VarhaiskasvatussuhdeViewSet)
router.register(r'paos-toiminnat', viewsets.PaosToimintaViewSet)
router.register(r'paos-oikeudet', viewsets.PaosOikeusViewSet)

# Nested routers are needed to support e.g. /api/v1/vakajarjestajat/33/toimipaikat/

nested_vakajarjestaja_router_ui = nested_routers.NestedSimpleRouter(router, r'vakajarjestajat', lookup='vakajarjestaja')
# /api/ui/vakajarjestajat/{id}/toimipaikat/
nested_vakajarjestaja_router_ui.register(r'toimipaikat', viewsets_ui.NestedToimipaikkaViewSet)
# /api/ui/vakajarjestajat/{id}/lapset/
nested_vakajarjestaja_router_ui.register(r'lapset', viewsets_ui.UiNestedLapsiViewSet)
# /api/ui/vakajarjestajat/{id}/tyontekijat/
nested_vakajarjestaja_router_ui.register(r'tyontekijat', viewsets_ui.UiNestedTyontekijaViewSet)
# /api/ui/all-vakajarjestajat/<id>/toimipaikat/
all_toimipaikat_router = nested_routers.NestedSimpleRouter(router, r'vakajarjestajat', lookup='vakajarjestaja')
all_toimipaikat_router.register(r'all-toimipaikat', viewsets_ui.NestedAllToimipaikkaViewSet)
# /api/ui/toimipaikat/
ui_toimipaikat_router = routers.SimpleRouter()
ui_toimipaikat_router.register(r'toimipaikat', viewsets.ToimipaikkaViewSet)

# /api/ui/all-vakajarjestajat/
vakajarjestaja_router = routers.SimpleRouter()
vakajarjestaja_router.register(r'all-vakajarjestajat', viewsets_ui.AllVakajarjestajaViewSet, basename='all-vakajarjestajat')
# /api/v1/vakajarjestajat/{id}/toimipaikat/
nested_vakajarjestaja_router = nested_routers.NestedSimpleRouter(router, r'vakajarjestajat', lookup='vakajarjestaja')
nested_vakajarjestaja_router.register(r'toimipaikat', viewsets.NestedToimipaikkaViewSet)
# /api/v1/vakajarjestajat/{id}/yhteenveto/
nested_vakajarjestaja_router.register(r'yhteenveto', viewsets.NestedVakajarjestajaYhteenvetoViewSet)
# /api/v1/vakajarjestajat/{id}/henkilohaku/
nested_vakajarjestaja_router.register('henkilohaku/lapset', viewsets.HenkilohakuLapset)
# /api/v1/vakajarjestajat/{id}/error-report-lapset/
nested_vakajarjestaja_router.register('error-report-lapset', viewsets_reporting.ErrorReportLapsetViewSet, basename='error-report-lapset')
# /api/v1/vakajarjestajat/{id}/error-report-tyontekijat/
nested_vakajarjestaja_router.register('error-report-tyontekijat', viewsets_reporting.ErrorReportTyontekijatViewSet, basename='error-report-tyontekijat')

nested_toimipaikka_router = nested_routers.NestedSimpleRouter(router, r'toimipaikat', lookup='toimipaikka')
# /api/v1/toimipaikat/{id}/toiminnallisetpainotukset/
nested_toimipaikka_router.register(r'toiminnallisetpainotukset', viewsets.NestedToiminnallinenPainotusViewSet)
# /api/v1/toimipaikat/{id}/kielipainotukset/
nested_toimipaikka_router.register(r'kielipainotukset', viewsets.NestedKieliPainotusViewSet)
# /api/v1/toimipaikat/{id}/varhaiskasvatussuhteet/
nested_toimipaikka_router.register(r'varhaiskasvatussuhteet', viewsets.NestedVarhaiskasvatussuhdeToimipaikkaViewSet)

nested_lapsi_router = nested_routers.NestedSimpleRouter(router, r'lapset', lookup='lapsi')
# /api/v1/lapset/{id}/huoltajat/
nested_lapsi_router.register(r'huoltajat', viewsets.NestedHuoltajaViewSet)
# /api/v1/lapset/{id}/varhaiskasvatuspaatokset/
nested_lapsi_router.register(r'varhaiskasvatuspaatokset', viewsets.NestedVarhaiskasvatuspaatosViewSet)
# /api/v1/lapset/{id}/maksutiedot/
nested_lapsi_router.register(r'maksutiedot', viewsets.NestedLapsiMaksutietoViewSet)
# /api/v1/lapset/{id}/varhaiskasvatussuhteet/
nested_lapsi_router.register(r'varhaiskasvatussuhteet', viewsets.NestedLapsenVarhaiskasvatussuhdeViewSet)
# /api/v1/lapset/{id}/kooste/
nested_lapsi_router.register(r'kooste', viewsets.NestedLapsiKoosteViewSet)

# /api/v1/huoltajat/{id}/lapset/
nested_huoltaja_router = nested_routers.NestedSimpleRouter(router_admin, r'huoltajat', lookup='huoltaja')
nested_huoltaja_router.register(r'lapset', viewsets.NestedLapsiViewSet)
# /api/v1/varhaiskasvatuspaatokset/{id}/varhaiskasvatussuhteet/
nested_varhaiskasvatuspaatos_router = nested_routers.NestedSimpleRouter(router, r'varhaiskasvatuspaatokset', lookup='varhaiskasvatuspaatos')
nested_varhaiskasvatuspaatos_router.register(r'varhaiskasvatussuhteet', viewsets.NestedVarhaiskasvatussuhdeViewSet)
# /api/v1/vakajarjestajat/{id}/paos-toimijat/
nested_vakajarjestaja_router.register(r'paos-toimijat', viewsets.NestedVakajarjestajaPaosToimijatViewSet)
# /api/v1/vakajarjestajat/{id}/paos-toimipaikat/
nested_vakajarjestaja_router.register(r'paos-toimipaikat', viewsets.NestedVakajarjestajaPaosToimipaikatViewSet)

# Routes for ONR-URLs
router_onr = routers.DefaultRouter()
router_onr.register(r'external-permissions', viewsets.ExternalPermissionsViewSet, 'external-permissions')

# Routes for Reporting-URLs
router_reporting = routers.DefaultRouter()
# /api/reporting/v1/tiedonsiirtotilasto/
router_reporting.register(r'tiedonsiirtotilasto', viewsets_reporting.TiedonsiirtotilastoViewSet, basename="tiedonsiirtotilasto")
# /api/reporting/v1/tiedonsiirto/
router_reporting.register(r'tiedonsiirto', viewsets_reporting.TiedonsiirtoViewSet, basename='tiedonsiirto')
# /api/reporting/v1/tiedonsiirto/yhteenveto/
router_reporting.register(r'tiedonsiirto/yhteenveto', viewsets_reporting.TiedonsiirtoYhteenvetoViewSet, basename='tiedonsiirto-yhteenveto')

router_kela_reporting = routers.DefaultRouter()
# /api/reporting/v1/kela/etuusmaksatus/aloittaneet
router_kela_reporting.register(r'aloittaneet', viewsets_reporting.KelaEtuusmaksatusAloittaneetViewset, basename='aloittaneet')
# /api/reporting/v1/kela/etuusmaksatus/lopettaneet
router_kela_reporting.register(r'lopettaneet', viewsets_reporting.KelaEtuusmaksatusLopettaneetViewSet, 'lopettaneet')
# /api/reporting/v1/kela/etuusmaksatus/maaraaikaiset
router_kela_reporting.register(r'maaraaikaiset', viewsets_reporting.KelaEtuusmaksatusMaaraaikaisetViewSet, 'maaraaikaset')
# /api/reporting/v1/kela/etuusmaksatus/korjaustiedot
router_kela_reporting.register(r'korjaustiedot', viewsets_reporting.KelaEtuusmaksatusKorjaustiedotViewSet, 'korjaustiedot')
# /api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut
router_kela_reporting.register(r'korjaustiedotpoistetut', viewsets_reporting.KelaEtuusmaksatusKorjaustiedotPoistetutViewSet, 'korjaustiedotpoistetut')

"""
router_reporting.register(r'lapset-ryhmittain', viewsets_reporting.LapsetRyhmittainViewSet, 'lapset-ryhmittain')
"""

# Routes for Oppija-URLs
router_oppija = routers.DefaultRouter()
# /api/oppija/v1/henkilotiedot/{oid}/
router_oppija.register(r'henkilotiedot', viewsets_oppija.HenkilotiedotViewSet)
# /api/oppija/v1/varhaiskasvatustiedot/{oid}/
router_oppija.register(r'varhaiskasvatustiedot', viewsets_oppija.VarhaiskasvatustiedotViewSet)
# /api/oppija/v1/huoltajatiedot/{oid}/
router_oppija.register(r'huoltajatiedot', viewsets_oppija.HuoltajatiedotViewSet)
# /api/oppija/v1/tyontekijatiedot/{oid}/
router_oppija.register(r'tyontekijatiedot', viewsets_oppija.TyontekijatiedotViewSet)

# Routes for Henkilöstö-URLs
router_henkilosto = routers.DefaultRouter()
router_henkilosto.register(r'tyontekijat', viewsets_henkilosto.TyontekijaViewSet)
router_henkilosto.register(r'tilapainen-henkilosto', viewsets_henkilosto.TilapainenHenkilostoViewSet)
router_henkilosto.register(r'tutkinnot', viewsets_henkilosto.TutkintoViewSet)
router_henkilosto.register(r'palvelussuhteet', viewsets_henkilosto.PalvelussuhdeViewSet)
router_henkilosto.register(r'tyoskentelypaikat', viewsets_henkilosto.TyoskentelypaikkaViewSet)
router_henkilosto.register(r'pidemmatpoissaolot', viewsets_henkilosto.PidempiPoissaoloViewSet)
router_henkilosto.register(r'taydennyskoulutukset', viewsets_henkilosto.TaydennyskoulutusViewSet)

nested_tyontekija_router = nested_routers.NestedSimpleRouter(router_henkilosto, r'tyontekijat', lookup='tyontekija')
# /api/henkilosto/v1/tyontekijat/{id}/kooste/
nested_tyontekija_router.register(r'kooste', viewsets_henkilosto.NestedTyontekijaKoosteViewSet)

# Routes for Julkinen-URLs
router_julkinen = routers.DefaultRouter()
# /api/julkinen/v1/koodistot/
router_julkinen.register(r'koodistot', viewsets_julkinen.KoodistotViewSet)
# /api/julkinen/v1/localisation/
router_julkinen.register(r'localisation', viewsets_julkinen.LocalisationViewSet, basename='get-localisation')

# In production environment public-app accesses iframes via nginx proxy, so we can use a stricter policy
xframe_options = xframe_options_sameorigin if settings.PRODUCTION_ENV or settings.QA_ENV else xframe_options_exempt

schema_view_public = get_schema_view_yasg(
    openapi.Info(
        title='VARDA REST API',
        default_version='v1',
    ),
    public=True,
    url='https://varda.example.com/api/',
    permission_classes=(permissions.AllowAny,),
    generator_class=PublicSchemaGenerator,
)
public_swagger_view = xframe_options(
    schema_view_public.as_cached_view(cache_timeout=0, cache_kwargs=None,
                                      renderer_classes=(PublicSwaggerRenderer,) + schema_view_public.renderer_classes)
)

excluded_model_regex = re.compile(r'^(historical.*)|(z\d.*)|(logdata)|(aikaleima)|(batcherror)$')
model_visualization_view = xframe_options(
    Plate.as_view(
        settings={
            'apps': ['varda'],
            'show_fields': False,
            'exclude': {'varda': [model.__name__.lower() for model in apps.get_app_config('varda').get_models()
                                  if excluded_model_regex.fullmatch(model.__name__.lower())]}}
    )
)

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^accounts/login$', django_cas_ng_views.LoginView.as_view(), name='cas_ng_login'),
    re_path(r'^accounts/logout$', django_cas_ng_views.LogoutView.as_view(), name='cas_ng_logout'),
    re_path(r'^accounts/callback$', django_cas_ng_views.CallbackView.as_view(), name='cas_ng_proxy_callback'),
    re_path(r'^accounts/huoltaja-login$', OppijaCasLoginView.as_view(), name='oppija_cas_ng_login'),
    re_path(r'^accounts/huoltaja-logout$', django_cas_ng_views.LogoutView.as_view(), name='oppija_cas_ng_logout'),
    re_path(r'^api/admin/', include(router_admin.urls), name='api_admin'),
    re_path(r'^api/pulssi/', include(router_pulssi.urls), name='api-pulssi'),
    re_path(r'^api/ui/', include(router_ui.urls), name='api-ui'),
    re_path(r'^api/ui/', include(nested_vakajarjestaja_router_ui.urls), name='nested-vakajarjestaja-api-ui'),
    re_path(r'^api/ui/', include(all_toimipaikat_router.urls), name='nested-all-vakajarjestaja-api-ui'),
    re_path(r'^api/ui/', include(ui_toimipaikat_router.urls), name='toimipaikat'),
    re_path(r'^api/ui/', include(vakajarjestaja_router.urls), name='all-vakajarjestaja-api-ui'),
    re_path(r'^api/user/', include(router_user.urls), name='api_user'),
    re_path(r'^api/v1/', include(router.urls), name='api-v1'),
    re_path(r'^api/v1/', include(nested_vakajarjestaja_router.urls), name='nested-vakajarjestaja-api-v1'),
    re_path(r'^api/v1/', include(nested_toimipaikka_router.urls), name='nested-toimipaikka-api-v1'),
    re_path(r'^api/v1/', include(nested_lapsi_router.urls), name='nested-lapsi-api-v1'),
    re_path(r'^api/admin/', include(nested_huoltaja_router.urls), name='nested-huoltaja-admin'),
    re_path(r'^api/v1/', include(nested_varhaiskasvatuspaatos_router.urls), name='nested-varhaiskasvatuspaatos-api-v1'),
    re_path(r'^api/v1/schema/', schema_view, name='schema-v1'),
    re_path(r'^api-auth/', include('varda.custom_login_urls', namespace='rest_framework'), name='api-auth'),
    re_path(r'^api/onr/', include(router_onr.urls), name='api-onr'),
    re_path(r'^api/reporting/v1/', include(router_reporting.urls), name='api-v1-reporting'),
    re_path(r'^api/reporting/v1/kela/etuusmaksatus/', include(router_kela_reporting.urls), name='kela-v1-reporting'),
    re_path(r'^varda/', include('varda.urls'), name='varda'),
    re_path(r'^api/henkilosto/v1/', include(router_henkilosto.urls), name='api-henkilosto-v1'),
    re_path(r'^api/henkilosto/v1/', include(nested_tyontekija_router.urls), name='api-nested-tyontekija-v1'),
    re_path(r'^api/oppija/v1/', include(router_oppija.urls), name='api-oppija-v1'),
    re_path(r'^api/julkinen/v1/', include(router_julkinen.urls), name='api-julkinen-v1'),
    re_path(r'^api/julkinen/v1/swagger/$', public_swagger_view, name='swagger-public'),
    re_path(r'^api/julkinen/v1/data-model/$', model_visualization_view, name='data-model-public'),
]
