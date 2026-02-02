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

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, re_path
from django.views.decorators.clickjacking import xframe_options_exempt, xframe_options_sameorigin
from django_spaghetti.views import Plate
from drf_yasg import openapi
from drf_yasg.views import get_schema_view as get_schema_view_yasg
from rest_framework import permissions, routers
from rest_framework.renderers import JSONRenderer
from rest_framework.schemas import get_schema_view
from rest_framework_nested import routers as nested_routers

from varda import (
    views,
    viewsets,
    viewsets_admin,
    viewsets_henkilosto,
    viewsets_julkinen,
    viewsets_oppija,
    viewsets_reporting,
    viewsets_ui,
    viewsets_luovutuspalvelu,
)
from varda.cas.cas_components import OppijaCasLoginView
from varda.constants import SWAGGER_DESCRIPTION
from varda.custom_swagger import PublicSchemaGenerator, PublicSwaggerRenderer
from varda.monkey_patch import cas_views, oppija_cas_views


# /api/admin/
router_admin = routers.DefaultRouter()
router_admin.register(r"users", viewsets.UserViewSet)
router_admin.register(r"groups", viewsets.GroupViewSet)
router_admin.register(r"update-henkilo", viewsets.UpdateHenkiloWithOid, basename="update-henkilo")
router_admin.register(r"huoltajat", viewsets.HuoltajaViewSet)
router_admin.register(r"huoltajuussuhteet", viewsets.HuoltajuussuhdeViewSet)
router_admin.register(r"clear-cache", viewsets.ClearCacheViewSet, basename="clear-cache")
router_admin.register(r"hae-yksiloimattomat", viewsets.HaeYksiloimattomatHenkilotViewSet, basename="hae-yksiloimattomat")
router_admin.register(
    r"anonymisointi-yhteenveto", viewsets_admin.AnonymisointiYhteenvetoViewSet, basename="anonymisointi-yhteenveto"
)
router_admin.register(r"duplicate-lapsi-objects", viewsets_reporting.DuplicateLapsiViewSet, basename="duplicate-lapsi-objects")
router_admin.register(r"set-paattymis-pvm", viewsets_admin.SetPaattymisPvmViewSet, basename="set-paattymis-pvm")
router_admin.register(r"get-muistutus-report", viewsets_admin.MuistutusReportViewSet, basename="get-muistutus-report")

# /api/admin/huoltajat/.../
router_admin_nested_huoltaja = nested_routers.NestedSimpleRouter(router_admin, r"huoltajat", lookup="huoltaja")
# /api/admin/huoltajat/{id}/lapset/
router_admin_nested_huoltaja.register(r"lapset", viewsets.NestedLapsiViewSet)

# /api/user/
router_user = routers.DefaultRouter()
router_user.register(r"data", viewsets.ActiveUserViewSet)
router_user.register(r"apikey", viewsets.ApikeyViewSet)

# /api/health/
router_health = routers.DefaultRouter()
router_health.register(r"", viewsets.HealthViewSet, "health")
router_health.register(r"vakajarjestajat", viewsets.HealthVakajarjestajatViewSet, basename="health-vakajarjestajat")

# /api/v1/
router = routers.DefaultRouter()
router.register(r"vakajarjestajat", viewsets.OrganisaatioViewSet)
router.register(r"toimipaikat", viewsets.ToimipaikkaViewSet)
router.register(r"toiminnallisetpainotukset", viewsets.ToiminnallinenPainotusViewSet)
router.register(r"kielipainotukset", viewsets.KieliPainotusViewSet)
router.register(r"hae-henkilo", viewsets.HaeHenkiloViewSet, "hae-henkilo")
router.register(r"henkilot", viewsets.HenkiloViewSet)
router.register(r"lapset", viewsets.LapsiViewSet)
router.register(r"maksutiedot", viewsets.MaksutietoViewSet)
router.register(r"varhaiskasvatuspaatokset", viewsets.VarhaiskasvatuspaatosViewSet)
router.register(r"varhaiskasvatussuhteet", viewsets.VarhaiskasvatussuhdeViewSet)
router.register(r"paos-toiminnat", viewsets.PaosToimintaViewSet)
router.register(r"paos-oikeudet", viewsets.PaosOikeusViewSet)
router.register(r"tukipaatokset", viewsets.TukipaatosViewSet)

# /api/v2/
router_v2 = routers.DefaultRouter()
router_v2.register(r"toimipaikat", viewsets.ToimipaikkaV2ViewSet)

# /api/v3/
router_v3 = routers.DefaultRouter()
router_v3.register(r"toimipaikat", viewsets.ToimipaikkaV3ViewSet)

# /api/v1/vakajarjestajat/.../
router_nested_vakajarjestaja = nested_routers.NestedSimpleRouter(router, r"vakajarjestajat", lookup="organisaatio")
# /api/v1/vakajarjestajat/{id}/toimipaikat/
router_nested_vakajarjestaja.register(r"toimipaikat", viewsets.NestedToimipaikkaViewSet)
# /api/v1/vakajarjestajat/{id}/yhteenveto/
router_nested_vakajarjestaja.register(r"yhteenveto", viewsets.NestedOrganisaatioYhteenvetoViewSet)
# /api/v1/vakajarjestajat/{id}/error-report-lapset/
router_nested_vakajarjestaja.register(
    "error-report-lapset", viewsets_reporting.ErrorReportLapsetViewSet, basename="error-report-lapset"
)
# /api/v1/vakajarjestajat/{id}/error-report-tyontekijat/
router_nested_vakajarjestaja.register(
    "error-report-tyontekijat", viewsets_reporting.ErrorReportTyontekijatViewSet, basename="error-report-tyontekijat"
)
# /api/v1/vakajarjestajat/{id}/error-report-toimipaikat/
router_nested_vakajarjestaja.register(
    "error-report-toimipaikat", viewsets_reporting.ErrorReportToimipaikatViewSet, basename="error-report-toimipaikat"
)
# /api/v1/vakajarjestajat/{id}/error-report-organisaatio/
router_nested_vakajarjestaja.register(
    "error-report-organisaatio", viewsets_reporting.ErrorReportOrganisaatioViewSet, basename="error-report-organisaatio"
)
# /api/v1/vakajarjestajat/{id}/paos-toimijat/
router_nested_vakajarjestaja.register(r"paos-toimijat", viewsets.NestedVakajarjestajaPaosToimijatViewSet)
# /api/v1/vakajarjestajat/{id}/paos-toimipaikat/
router_nested_vakajarjestaja.register(
    r"paos-toimipaikat", viewsets.NestedVakajarjestajaPaosToimipaikatViewSet, basename="paos-toimipaikat"
)

# /api/v1/toimipaikat/.../
router_nested_toimipaikka = nested_routers.NestedSimpleRouter(router, r"toimipaikat", lookup="toimipaikka")
# /api/v1/toimipaikat/{id}/toiminnallisetpainotukset/
router_nested_toimipaikka.register(r"toiminnallisetpainotukset", viewsets.NestedToiminnallinenPainotusViewSet)
# /api/v1/toimipaikat/{id}/kielipainotukset/
router_nested_toimipaikka.register(r"kielipainotukset", viewsets.NestedKieliPainotusViewSet)
# /api/v1/toimipaikat/{id}/varhaiskasvatussuhteet/
router_nested_toimipaikka.register(r"varhaiskasvatussuhteet", viewsets.NestedVarhaiskasvatussuhdeToimipaikkaViewSet)

# /api/v1/lapset/.../
router_nested_lapsi = nested_routers.NestedSimpleRouter(router, r"lapset", lookup="lapsi")
# /api/v1/lapset/{id}/huoltajat/
router_nested_lapsi.register(r"huoltajat", viewsets.NestedHuoltajaViewSet)
# /api/v1/lapset/{id}/varhaiskasvatuspaatokset/
router_nested_lapsi.register(r"varhaiskasvatuspaatokset", viewsets.NestedVarhaiskasvatuspaatosViewSet)
# /api/v1/lapset/{id}/maksutiedot/
router_nested_lapsi.register(r"maksutiedot", viewsets.NestedLapsiMaksutietoViewSet)
# /api/v1/lapset/{id}/varhaiskasvatussuhteet/
router_nested_lapsi.register(r"varhaiskasvatussuhteet", viewsets.NestedLapsenVarhaiskasvatussuhdeViewSet)
# /api/v1/lapset/{id}/kooste/
router_nested_lapsi.register(r"kooste", viewsets.NestedLapsiKoosteViewSet)

# /api/v1/varhaiskasvatuspaatokset/.../
router_nested_varhaiskasvatuspaatos = nested_routers.NestedSimpleRouter(
    router, r"varhaiskasvatuspaatokset", lookup="varhaiskasvatuspaatos"
)
# /api/v1/varhaiskasvatuspaatokset/{id}/varhaiskasvatussuhteet/
router_nested_varhaiskasvatuspaatos.register(r"varhaiskasvatussuhteet", viewsets.NestedVarhaiskasvatussuhdeViewSet)

# /api/ui/
router_ui = routers.DefaultRouter()
router_ui.register(r"vakajarjestajat", viewsets_ui.UiVakajarjestajatViewSet, basename="hae-vakajarjestajat")
router_ui.register(r"all-vakajarjestajat", viewsets_ui.AllVakajarjestajaViewSet, basename="all-vakajarjestajat")
router_ui.register(r"active-organisaatio", viewsets_ui.ActiveOrganisaatioViewSet, basename="active-organisaatio")

# /api/ui/vakajarjestajat/.../
router_ui_nested_vakajarjestaja = nested_routers.NestedSimpleRouter(router_ui, r"vakajarjestajat", lookup="organisaatio")
# /api/ui/vakajarjestajat/{id}/toimipaikat/
router_ui_nested_vakajarjestaja.register(r"toimipaikat", viewsets_ui.NestedToimipaikkaViewSet)
# /api/ui/vakajarjestajat/{id}/lapset/
router_ui_nested_vakajarjestaja.register(r"lapset", viewsets_ui.UiNestedLapsiViewSet)
# /api/ui/vakajarjestajat/{id}/tyontekijat/
router_ui_nested_vakajarjestaja.register(r"tyontekijat", viewsets_ui.UiNestedTyontekijaViewSet)
# /api/ui/vakajarjestajat/{id}/all-toimipaikat/
router_ui_nested_vakajarjestaja.register(r"all-toimipaikat", viewsets_ui.NestedAllToimipaikkaViewSet, basename="all-toimipaikat")

# /api/onr/
router_onr = routers.DefaultRouter()
router_onr.register(r"external-permissions", viewsets.ExternalPermissionsViewSet, "external-permissions")

# /api/reporting/
router_reporting = routers.DefaultRouter()
# /api/reporting/v1/tiedonsiirtotilasto/
router_reporting.register(r"tiedonsiirtotilasto", viewsets_reporting.TiedonsiirtotilastoViewSet, basename="tiedonsiirtotilasto")
# /api/reporting/v1/tiedonsiirto/
router_reporting.register(r"tiedonsiirto", viewsets_reporting.TiedonsiirtoViewSet, basename="tiedonsiirto")
# /api/reporting/v1/tiedonsiirto/yhteenveto/
router_reporting.register(
    r"tiedonsiirto/yhteenveto", viewsets_reporting.TiedonsiirtoYhteenvetoViewSet, basename="tiedonsiirto-yhteenveto"
)
# /api/reporting/v1/excel-reports/
router_reporting.register(r"excel-reports", viewsets_reporting.ExcelReportViewSet, basename="excel-reports")
# /api/reporting/v1/transfer-outage/
router_reporting.register(r"transfer-outage", viewsets_reporting.TransferOutageReportViewSet, basename="transfer-outage")
# /api/reporting/v1/request-summary/
router_reporting.register(r"request-summary", viewsets_reporting.RequestSummaryViewSet, basename="request-summary")

# /api/reporting/v1/kela/etuusmaksatus/
router_kela_reporting = routers.DefaultRouter()
router_kela_reporting.register(r"aloittaneet", viewsets_reporting.KelaEtuusmaksatusAloittaneetViewset, basename="aloittaneet")
router_kela_reporting.register(r"lopettaneet", viewsets_reporting.KelaEtuusmaksatusLopettaneetViewSet, "lopettaneet")
router_kela_reporting.register(r"maaraaikaiset", viewsets_reporting.KelaEtuusmaksatusMaaraaikaisetViewSet, "maaraaikaset")
router_kela_reporting.register(r"korjaustiedot", viewsets_reporting.KelaEtuusmaksatusKorjaustiedotViewSet, "korjaustiedot")
router_kela_reporting.register(
    r"korjaustiedotpoistetut", viewsets_reporting.KelaEtuusmaksatusKorjaustiedotPoistetutViewSet, "korjaustiedotpoistetut"
)

# /api/reporting/v2/kela/etuusmaksatus/
router_kela_reporting_v2 = routers.DefaultRouter()
router_kela_reporting_v2.register(
    r"aloittaneet", viewsets_reporting.KelaEtuusmaksatusAloittaneetV2Viewset, basename="aloittaneet-v2"
)
router_kela_reporting_v2.register(r"lopettaneet", viewsets_reporting.KelaEtuusmaksatusLopettaneetV2ViewSet, "lopettaneet-v2")
router_kela_reporting_v2.register(r"maaraaikaiset", viewsets_reporting.KelaEtuusmaksatusMaaraaikaisetV2ViewSet, "maaraaikaset-v2")
router_kela_reporting_v2.register(
    r"korjaustiedot", viewsets_reporting.KelaEtuusmaksatusKorjaustiedotV2ViewSet, "korjaustiedot-v2"
)
router_kela_reporting_v2.register(
    r"korjaustiedotpoistetut", viewsets_reporting.KelaEtuusmaksatusKorjaustiedotPoistetutV2ViewSet, "korjaustiedotpoistetut-v2"
)

# /api/reporting/v1/tilastokeskus/
router_tilastokeskus_reporting = routers.DefaultRouter()
router_tilastokeskus_reporting.register(r"organisaatiot", viewsets_reporting.TkOrganisaatiot, basename="tk-organisaatiot")
router_tilastokeskus_reporting.register(
    r"varhaiskasvatustiedot", viewsets_reporting.TkVakatiedot, basename="tk-varhaiskasvatustiedot"
)
router_tilastokeskus_reporting.register(
    r"henkilostotiedot", viewsets_reporting.TkHenkilostotiedot, basename="tk-henkilostotiedot"
)

# /api/reporting/v1/valssi/
router_valssi_reporting = routers.DefaultRouter()
router_valssi_reporting.register(r"organisaatiot", viewsets_reporting.ValssiOrganisaatioViewSet, basename="valssi-organisaatiot")
router_valssi_reporting.register(r"toimipaikat", viewsets_reporting.ValssiToimipaikkaViewSet, basename="valssi-toimipaikat")

# /api/reporting/v1/valssi/organisaatiot/.../
router_valssi_reporting_nested_organisaatio = nested_routers.NestedSimpleRouter(
    router_valssi_reporting, r"organisaatiot", lookup="organisaatio"
)
# /api/reporting/v1/valssi/organisaatiot/{id}/taustatiedot/
router_valssi_reporting_nested_organisaatio.register(r"taustatiedot", viewsets_reporting.ValssiTaustatiedotViewSet)

# /api/reporting/v1/valssi/toimipaikat/.../
router_valssi_reporting_nested_toimipaikka = nested_routers.NestedSimpleRouter(
    router_valssi_reporting, r"toimipaikat", lookup="toimipaikka"
)
# /api/reporting/v1/valssi/toimipaikat/{id}/tyontekijat/
router_valssi_reporting_nested_toimipaikka.register(r"tyontekijat", viewsets_reporting.ValssiTyontekijaViewSet)

# /api/reporting/v1/vipunen/
router_vipunen_reporting = routers.DefaultRouter()
router_vipunen_reporting.register(
    r"organisaatiot", viewsets_reporting.VipunenOrganisaatioViewSet, basename="vipunen-organisaatiot"
)
router_vipunen_reporting.register(
    r"vuokrattu-henkilosto", viewsets_reporting.VipunenVuokrattuHenkilostoViewSet, basename="vipunen-vuokrattu-henkilosto"
)
router_vipunen_reporting.register(r"toimipaikat", viewsets_reporting.VipunenToimipaikkaViewSet, basename="vipunen-toimipaikat")
router_vipunen_reporting.register(
    r"toiminnallisetpainotukset",
    viewsets_reporting.VipunenToiminnallinenPainotusViewSet,
    basename="vipunen-toiminnallisetpainotukset",
)
router_vipunen_reporting.register(
    r"kielipainotukset", viewsets_reporting.VipunenKielipainotusViewSet, basename="vipunen-kielipainotukset"
)
router_vipunen_reporting.register(r"lapset", viewsets_reporting.VipunenLapsiViewSet, basename="vipunen-lapset")
router_vipunen_reporting.register(
    r"varhaiskasvatuspaatokset",
    viewsets_reporting.VipunenVarhaiskasvatuspaatosViewSet,
    basename="vipunen-varhaiskasvatuspaatokset",
)
router_vipunen_reporting.register(
    r"varhaiskasvatussuhteet", viewsets_reporting.VipunenVarhaiskasvatussuhdeViewSet, basename="vipunen-varhaiskasvatussuhteet"
)
router_vipunen_reporting.register(r"maksutiedot", viewsets_reporting.VipunenMaksutietoViewSet, basename="vipunen-maksutiedot")
router_vipunen_reporting.register(r"tyontekijat", viewsets_reporting.VipunenTyontekijaViewSet, basename="vipunen-tyontekijat")
router_vipunen_reporting.register(r"tutkinnot", viewsets_reporting.VipunenTutkintoViewSet, basename="vipunen-tutkinnot")
router_vipunen_reporting.register(
    r"palvelussuhteet", viewsets_reporting.VipunenPalvelussuhdeViewSet, basename="vipunen-palvelussuhteet"
)
router_vipunen_reporting.register(
    r"tyoskentelypaikat", viewsets_reporting.VipunenTyoskentelypaikkaViewSet, basename="vipunen-tyoskentelypaikat"
)
router_vipunen_reporting.register(
    r"pidemmatpoissaolot", viewsets_reporting.VipunenPidempiPoissaoloViewSet, basename="vipunen-pidemmatpoissaolot"
)
router_vipunen_reporting.register(
    r"taydennyskoulutus-tyontekijat",
    viewsets_reporting.VipunenTaydennyskoulutusTyontekijaViewSet,
    basename="vipunen-taydennyskoulutus-tyontekijat",
)
router_vipunen_reporting.register(
    r"taydennyskoulutukset", viewsets_reporting.VipunenTaydennyskoulutusViewSet, basename="vipunen-taydennyskoulutukset"
)
router_vipunen_reporting.register(r"tuentiedot", viewsets_reporting.VipunenTuenTiedotViewSet, basename="vipunen-tuentiedot")

# /api/oppija/v1/
router_oppija = routers.DefaultRouter()
# /api/oppija/v1/henkilotiedot/{oid}/
router_oppija.register(r"henkilotiedot", viewsets_oppija.HenkilotiedotViewSet)
# /api/oppija/v1/varhaiskasvatustiedot/{oid}/
router_oppija.register(r"varhaiskasvatustiedot", viewsets_oppija.VarhaiskasvatustiedotViewSet, basename="varhaiskasvatustiedot")
# /api/oppija/v1/huoltajatiedot/{oid}/
router_oppija.register(r"huoltajatiedot", viewsets_oppija.HuoltajatiedotViewSet, basename="huoltajatiedot")
# /api/oppija/v1/tyontekijatiedot/{oid}/
router_oppija.register(r"tyontekijatiedot", viewsets_oppija.TyontekijatiedotViewSet, basename="tyontekijatiedot")

# /api/henkilosto/v1/
router_henkilosto = routers.DefaultRouter()
router_henkilosto.register(r"tyontekijat", viewsets_henkilosto.TyontekijaViewSet)
router_henkilosto.register(r"tilapainen-henkilosto", viewsets_henkilosto.VuokrattuHenkilostoViewSet)
router_henkilosto.register(r"tutkinnot", viewsets_henkilosto.TutkintoViewSet)
router_henkilosto.register(r"palvelussuhteet", viewsets_henkilosto.PalvelussuhdeViewSet)
router_henkilosto.register(r"tyoskentelypaikat", viewsets_henkilosto.TyoskentelypaikkaViewSet)
router_henkilosto.register(r"pidemmatpoissaolot", viewsets_henkilosto.PidempiPoissaoloViewSet)
router_henkilosto.register(r"taydennyskoulutukset", viewsets_henkilosto.TaydennyskoulutusViewSet)

# /api/henkilosto/v1/tyontekijat/.../
router_henkilosto_nested_tyontekija = nested_routers.NestedDefaultRouter(router_henkilosto, r"tyontekijat", lookup="tyontekija")
# /api/henkilosto/v1/tyontekijat/{id}/kooste/
router_henkilosto_nested_tyontekija.register(r"kooste", viewsets_henkilosto.NestedTyontekijaKoosteViewSet)

# /api/henkilosto/v2/
router_henkilosto_v2 = routers.DefaultRouter()
router_henkilosto_v2.register(
    r"taydennyskoulutukset", viewsets_henkilosto.TaydennyskoulutusV2ViewSet, basename="taydennyskoulutukset-v2"
)
router_henkilosto_v2.register(
    r"tyoskentelypaikat", viewsets_henkilosto.TyoskentelypaikkaV2ViewSet, basename="tyoskentelypaikat-v2"
)

# /api/julkinen/v1/
router_julkinen = routers.DefaultRouter()
router_julkinen.register(r"koodistot", viewsets_julkinen.KoodistotViewSet)
router_julkinen.register(r"localisation", viewsets_julkinen.LocalisationViewSet, basename="get-localisation")
router_julkinen.register(r"pulssi", viewsets_julkinen.PulssiViewSet, basename="get-pulssi")

# Luovutuspalvelu /api/client/v1/
router_client = routers.DefaultRouter()
router_client.register(r"csr", viewsets_luovutuspalvelu.CsrViewset, basename="luovutuspalvelu-csr")

# /api/v1/schema/
schema_view = get_schema_view(title="VARDA API", renderer_classes=[JSONRenderer])

# In production environment public-app accesses iframes via nginx proxy, so we can use a stricter policy
xframe_options = xframe_options_sameorigin if settings.PRODUCTION_ENV or settings.QA_ENV else xframe_options_exempt

# /api/julkinen/v1/swagger/
schema_view_public = get_schema_view_yasg(
    openapi.Info(title="VARDA REST API", default_version="v1", description=SWAGGER_DESCRIPTION),
    public=True,
    url="https://varda.example.com/api/",
    permission_classes=(permissions.AllowAny,),
    generator_class=PublicSchemaGenerator,
)
public_swagger_view = xframe_options(
    schema_view_public.as_cached_view(
        cache_timeout=0, cache_kwargs=None, renderer_classes=(PublicSwaggerRenderer,) + schema_view_public.renderer_classes
    )
)

# /api/julkinen/v1/data-model/
excluded_model_regex = re.compile(r"^(historical.*)|(z\d.*)|(logdata)|(aikaleima)|(batcherror)|(logincertificate)$")
model_visualization_view = xframe_options(
    Plate.as_view(
        settings={
            "apps": ["varda"],
            "show_fields": False,
            "exclude": {
                "varda": [
                    model.__name__.lower()
                    for model in apps.get_app_config("varda").get_models()
                    if excluded_model_regex.fullmatch(model.__name__.lower())
                ]
            },
        }
    )
)

urlpatterns = [
    re_path(r"^$", views.index, name="index"),
    re_path(r"^admin/", admin.site.urls, name="admin"),
    re_path(r"^varda/", include("varda.urls"), name="varda"),
    re_path(r"^accounts/login$", cas_views.LoginView.as_view(), name="cas_ng_login"),
    re_path(r"^accounts/logout$", cas_views.LogoutView.as_view(), name="cas_ng_logout"),
    re_path(r"^accounts/callback$", cas_views.CallbackView.as_view(), name="cas_ng_proxy_callback"),
    re_path(r"^accounts/huoltaja-login$", OppijaCasLoginView.as_view(), name="oppija_cas_ng_login"),
    re_path(r"^accounts/huoltaja-logout$", oppija_cas_views.LogoutView.as_view(), name="oppija_cas_ng_logout"),
    re_path(r"^accounts/password-reset/?$", auth_views.PasswordResetView.as_view(), name="admin_password_reset"),
    re_path(r"^accounts/password-reset/done/?$", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    re_path(
        r"^accounts/reset/(?P<uidb64>.+)/(?P<token>.+)/?$",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    re_path(r"^accounts/reset/done/?$", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    re_path(r"^api-auth/", include("varda.custom_login_urls", namespace="rest_framework"), name="api_auth"),
    re_path(r"^api/onr/", include(router_onr.urls), name="api_onr"),
    re_path(r"^api/user/", include(router_user.urls), name="api_user"),
    re_path(r"^api/admin/", include(router_admin.urls), name="api_admin"),
    re_path(r"^api/admin/", include(router_admin_nested_huoltaja.urls), name="api_admin_nested_huoltaja"),
    re_path(r"^api/health/", include(router_health.urls), name="api_health"),
    re_path(r"^api/ui/", include(router_ui.urls), name="api_ui"),
    re_path(r"^api/ui/", include(router_ui_nested_vakajarjestaja.urls), name="api_ui_nested_vakajarjestaja"),
    re_path(r"^api/v3/", include(router_v3.urls), name="api_v3"),
    re_path(r"^api/v2/", include(router_v2.urls), name="api_v2"),
    re_path(r"^api/v1/", include(router.urls), name="api_v1"),
    re_path(r"^api/v1/", include(router_nested_vakajarjestaja.urls), name="api_v1_nested_vakajarjestaja"),
    re_path(r"^api/v1/", include(router_nested_toimipaikka.urls), name="api_v1_nested_toimipaikka"),
    re_path(r"^api/v1/", include(router_nested_lapsi.urls), name="api_v1_nested_lapsi"),
    re_path(r"^api/v1/", include(router_nested_varhaiskasvatuspaatos.urls), name="api_v1_nested_varhaiskasvatuspaatos"),
    re_path(r"^api/v1/schema/", schema_view, name="api_v1_schema"),
    re_path(r"^api/reporting/v1/", include(router_reporting.urls), name="api_reporting_v1"),
    re_path(r"^api/reporting/v1/kela/etuusmaksatus/", include(router_kela_reporting.urls), name="api_reporting_v1_kela"),
    re_path(r"^api/reporting/v2/kela/etuusmaksatus/", include(router_kela_reporting_v2.urls), name="api_reporting_v2_kela"),
    re_path(
        r"^api/reporting/v1/tilastokeskus/", include(router_tilastokeskus_reporting.urls), name="api_reporting_v1_tilastokeskus"
    ),
    re_path(r"^api/reporting/v1/valssi/", include(router_valssi_reporting.urls), name="api_reporting_v1_valssi"),
    re_path(
        r"^api/reporting/v1/valssi/",
        include(router_valssi_reporting_nested_organisaatio.urls),
        name="api_reporting_v1_valssi_nested_organisaatio",
    ),
    re_path(
        r"^api/reporting/v1/valssi/",
        include(router_valssi_reporting_nested_toimipaikka.urls),
        name="api_reporting_v1_valssi_nested_toimipaikka",
    ),
    re_path(r"^api/reporting/v1/vipunen/", include(router_vipunen_reporting.urls), name="api_reporting_v1_vipunen"),
    re_path(r"^api/henkilosto/v1/", include(router_henkilosto.urls), name="api_henkilosto_v1"),
    re_path(
        r"^api/henkilosto/v1/", include(router_henkilosto_nested_tyontekija.urls), name="api_henkilosto_v1_nested_tyontekija"
    ),
    re_path(r"^api/henkilosto/v2/", include(router_henkilosto_v2.urls), name="api_henkilosto_v2"),
    re_path(r"^api/oppija/v1/", include(router_oppija.urls), name="api_oppija_v1"),
    re_path(r"^api/julkinen/v1/", include(router_julkinen.urls), name="api_julkinen_v1"),
    re_path(r"^api/client/v1/", include(router_client.urls), name="api_client_v1"),
    re_path(r"^api/julkinen/v1/swagger/$", public_swagger_view, name="api_julkinen_v1_swagger"),
    re_path(r"^api/julkinen/v1/data-model/$", model_visualization_view, name="api_julkinen_v1_data_model"),
    re_path(r"^ping/", views.ping, name="ping"),
]
