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
import django_cas_ng.views as django_cas_ng_views

from django.contrib import admin
from django.urls import include, re_path
from rest_framework import routers
from rest_framework_nested import routers as nested_routers

import varda.viewsets_ui
from varda import views, viewsets, viewsets_reporting, viewsets_ui, viewsets_oppija, viewsets_henkilosto
from varda.cas.oppija_cas_views import OppijaCasLoginView
from rest_framework.renderers import CoreJSONRenderer
from rest_framework.schemas import get_schema_view

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

# /api/ui/vakajarjestajat/{id}/toimipaikat/
nested_vakajarjestaja_router_ui = nested_routers.NestedSimpleRouter(router, r'vakajarjestajat', lookup='vakajarjestaja')
nested_vakajarjestaja_router_ui.register(r'toimipaikat', viewsets_ui.NestedToimipaikkaViewSet)
# /api/ui/all-vakajarjestajat/<id>/toimipaikat/
all_toimipaikat_router = nested_routers.NestedSimpleRouter(router, r'vakajarjestajat', lookup='vakajarjestaja')
all_toimipaikat_router.register(r'all-toimipaikat', varda.viewsets_ui.NestedAllToimipaikkaViewSet)
# /api/ui/toimipaikat/
ui_toimipaikat_router = routers.SimpleRouter()
ui_toimipaikat_router.register(r'toimipaikat', viewsets.ToimipaikkaViewSet)
# /api/ui/toimipaikat/<id>/lapset/
nested_ui_toimipaikat_lapset_router = nested_routers.NestedSimpleRouter(router, r'toimipaikat', lookup='toimipaikka')
nested_ui_toimipaikat_lapset_router.register(r'lapset', viewsets_ui.NestedToimipaikanLapsetViewSet, basename='toimipaikan-lapset')


# /api/ui/all-vakajarjestajat/
vakajarjestaja_router = routers.SimpleRouter()
vakajarjestaja_router.register(r'all-vakajarjestajat', varda.viewsets_ui.AllVakajarjestajaViewSet, basename='all-vakajarjestajat')
# /api/v1/vakajarjestajat/{id}/toimipaikat/
nested_vakajarjestaja_router = nested_routers.NestedSimpleRouter(router, r'vakajarjestajat', lookup='vakajarjestaja')
nested_vakajarjestaja_router.register(r'toimipaikat', viewsets.NestedToimipaikkaViewSet)
# /api/v1/vakajarjestajat/{id}/yhteenveto/
nested_vakajarjestaja_router.register(r'yhteenveto', viewsets.NestedVakajarjestajaYhteenvetoViewSet)
# /api/v1/vakajarjestajat/{id}/henkilohaku/
nested_vakajarjestaja_router.register('henkilohaku/lapset', viewsets.HenkilohakuLapset)
# /api/v1/toimipaikat/{id}/toiminnallisetpainotukset/
nested_toimipaikka_router_1 = nested_routers.NestedSimpleRouter(router, r'toimipaikat', lookup='toimipaikka')
nested_toimipaikka_router_1.register(r'toiminnallisetpainotukset', viewsets.NestedToiminnallinenPainotusViewSet)
# /api/v1/toimipaikat/{id}/kielipainotukset/
nested_toimipaikka_router_2 = nested_routers.NestedSimpleRouter(router, r'toimipaikat', lookup='toimipaikka')
nested_toimipaikka_router_2.register(r'kielipainotukset', viewsets.NestedKieliPainotusViewSet)
# /api/v1/toimipaikka/{id}/varhaiskasvatussuhteet/
nested_toimipaikka_router_4 = nested_routers.NestedSimpleRouter(router, r'toimipaikat', lookup='toimipaikka')
nested_toimipaikka_router_4.register(r'varhaiskasvatussuhteet', viewsets.NestedVarhaiskasvatussuhdeToimipaikkaViewSet)
# /api/v1/lapset/{id}/huoltajat/
nested_lapsi_router_1 = nested_routers.NestedSimpleRouter(router, r'lapset', lookup='lapsi')
nested_lapsi_router_1.register(r'huoltajat', viewsets.NestedHuoltajaViewSet)
# /api/v1/lapset/{id}/varhaiskasvatuspaatokset/
nested_lapsi_router_2 = nested_routers.NestedSimpleRouter(router, r'lapset', lookup='lapsi')
nested_lapsi_router_2.register(r'varhaiskasvatuspaatokset', viewsets.NestedVarhaiskasvatuspaatosViewSet)
# /api/v1/lapset/{id}/maksutiedot/
nested_lapsi_router_2.register(r'maksutiedot', viewsets.NestedLapsiMaksutietoViewSet)
# /api/v1/lapset/{id}/varhaiskasvatussuhteet/
nested_lapsi_router_3 = nested_routers.NestedSimpleRouter(router, r'lapset', lookup='lapsi')
nested_lapsi_router_3.register(r'varhaiskasvatussuhteet', viewsets.NestedLapsenVarhaiskasvatussuhdeViewSet)
# /api/v1/lapset/{id}/kooste/
nested_lapsi_router_3.register(r'kooste', viewsets.NestedLapsiKoosteViewSet)
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
router_reporting.register(r'kelaraportti', viewsets_reporting.KelaRaporttiViewSet, 'kelaraportti')
# /reporting/api/v1/tiedonsiirtotilasto/
router_reporting.register(r'tiedonsiirtotilasto', viewsets_reporting.TiedonsiirtotilastoViewSet, basename="tiedonsiirtotilasto")
"""
router_reporting.register(r'lapset-ryhmittain', viewsets_reporting.LapsetRyhmittainViewSet, 'lapset-ryhmittain')
"""

router_koodisto = routers.DefaultRouter()
router_koodisto.register(r'koodit', viewsets_reporting.KoodistoViewSet, 'koodisto')

"""
Routers for oppija
"""
router_oppija = routers.DefaultRouter()

# Routes for Henkilöstö-URLs

router_henkilosto = routers.DefaultRouter()
router_henkilosto.register(r'tyontekijat', viewsets_henkilosto.TyontekijaViewSet)
router_henkilosto.register(r'tilapainen-henkilosto', viewsets_henkilosto.TilapainenHenkilostoViewSet)
router_henkilosto.register(r'tutkinnot', viewsets_henkilosto.TutkintoViewSet)
router_henkilosto.register(r'palvelussuhteet', viewsets_henkilosto.PalvelussuhdeViewSet)

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
    re_path(r'^api/ui/', include(nested_ui_toimipaikat_lapset_router.urls), name='nested-toimipaikat-lapset-api-ui'),
    re_path(r'^api/ui/', include(vakajarjestaja_router.urls), name='all-vakajarjestaja-api-ui'),
    re_path(r'^api/user/', include(router_user.urls), name='api_user'),
    re_path(r'^api/v1/', include(router.urls), name='api-v1'),
    re_path(r'^api/v1/', include(nested_vakajarjestaja_router.urls), name='nested-vakajarjestaja-api-v1'),
    re_path(r'^api/v1/', include(nested_toimipaikka_router_1.urls), name='nested-toimipaikka-1-api-v1'),
    re_path(r'^api/v1/', include(nested_toimipaikka_router_2.urls), name='nested-toimipaikka-2-api-v1'),
    re_path(r'^api/v1/', include(nested_toimipaikka_router_4.urls), name='nested-toimipaikka-4-api-v1'),
    re_path(r'^api/v1/', include(nested_lapsi_router_1.urls), name='nested-lapsi-1-api-v1'),
    re_path(r'^api/v1/', include(nested_lapsi_router_2.urls), name='nested-lapsi-2-api-v1'),
    re_path(r'^api/v1/', include(nested_lapsi_router_3.urls), name='nested-lapsi-3-api-v1'),
    re_path(r'^api/admin/', include(nested_huoltaja_router.urls), name='nested-huoltaja-admin'),
    re_path(r'^api/v1/', include(nested_varhaiskasvatuspaatos_router.urls), name='nested-varhaiskasvatuspaatos-api-v1'),
    re_path(r'^api/v1/schema/', schema_view, name='schema-v1'),
    re_path(r'^api-auth/', include('varda.custom_login_urls', namespace='rest_framework'), name='api-auth'),
    re_path(r'^api/onr/', include(router_onr.urls), name='api-onr'),
    re_path(r'^reporting/api/v1/', include(router_reporting.urls), name='api-v1-reporting'),
    re_path(r'^koodisto/api/v1/', include(router_koodisto.urls), name='koodisto'),
    re_path(r'^varda/', include('varda.urls'), name='varda'),
    re_path(r'^api/henkilosto/v1/', include(router_henkilosto.urls), name='api-henkilosto-v1'),
    re_path(r'^api/oppija/v1/', include(router_oppija.urls), name='oppija-api-v1'),
    re_path(r'^api/oppija/v1/huoltajanlapsi/(?P<henkilo_oid>[.0-9]{26,})/$',
            viewsets_oppija.HuoltajanLapsiViewSet.as_view({'get': 'retrieve'}), name='huoltajanlapsi'),
]
