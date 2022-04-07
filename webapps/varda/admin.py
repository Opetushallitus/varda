from django.contrib import admin
from django.contrib.admin import display, ModelAdmin
from django.contrib.auth.models import User
from guardian.admin import GuardedModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import (Aikaleima, BatchError, Henkilo, Huoltaja, Huoltajuussuhde, KieliPainotus, Lapsi, LoginCertificate,
                     Maksutieto, MaksutietoHuoltajuussuhde, TaydennyskoulutusTyontekija, Tyoskentelypaikka,
                     Palvelussuhde, PaosOikeus, PaosToiminta, TilapainenHenkilosto, ToiminnallinenPainotus, Toimipaikka,
                     Tutkinto, Tyontekija, Organisaatio, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, PidempiPoissaolo,
                     Taydennyskoulutus, YearlyReportSummary, Z3_AdditionalCasUserFields, Z7_AdditionalUserFields)


class AdminWithGuardianAndHistory(GuardedModelAdmin, SimpleHistoryAdmin):
    pass


class OrganisaatioAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'nimi', 'organisaatio_oid',)
    search_fields = ('=id', 'nimi', '=organisaatio_oid',)


class ToimipaikkaAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'nimi', 'organisaatio_oid',)
    search_fields = ('=id', 'nimi', '=organisaatio_oid',)
    raw_id_fields = ('vakajarjestaja',)


class ToiminnallinenPainotusAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'toimintapainotus_koodi', 'toimipaikka',)
    search_fields = ('=id', '=toimintapainotus_koodi', '=toimipaikka__id',)
    raw_id_fields = ('toimipaikka',)


class KieliPainotusAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'kielipainotus_koodi', 'toimipaikka',)
    search_fields = ('=id', '=kielipainotus_koodi', '=toimipaikka__id',)
    raw_id_fields = ('toimipaikka',)


class HenkiloAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'etunimet', 'sukunimi', 'henkilo_oid',)
    search_fields = ('=id', 'etunimet', 'sukunimi', '=henkilo_oid',)


class LapsiAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'get_henkilo_oid', 'get_vakatoimija_oid', 'get_oma_organisaatio_oid',
                    'get_paos_organisaatio_oid',)
    search_fields = ('=id', '=vakatoimija__organisaatio_oid', '=oma_organisaatio__organisaatio_oid',
                     '=paos_organisaatio__organisaatio_oid', '=henkilo__henkilo_oid',)
    raw_id_fields = ('henkilo', 'vakatoimija', 'oma_organisaatio', 'paos_organisaatio',)

    @display(ordering='henkilo__henkilo_oid', description='henkilo_oid')
    def get_henkilo_oid(self, instance):
        return instance.henkilo.henkilo_oid

    @display(ordering='vakatoimija__organisaatio_oid', description='vakatoimija organisaatio_oid')
    def get_vakatoimija_oid(self, instance):
        return getattr(instance.vakatoimija, 'organisaatio_oid', None)

    @display(ordering='oma_organisaatio__organisaatio_oid', description='oma_organisaatio organisaatio_oid')
    def get_oma_organisaatio_oid(self, instance):
        return getattr(instance.oma_organisaatio, 'organisaatio_oid', None)

    @display(ordering='paos_organisaatio__organisaatio_oid', description='paos_organisaatio organisaatio_oid')
    def get_paos_organisaatio_oid(self, instance):
        return getattr(instance.paos_organisaatio, 'organisaatio_oid', None)


class VarhaiskasvatuspaatosAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'lapsi',)
    search_fields = ('=id', '=lapsi__id',)
    raw_id_fields = ('lapsi',)


class VarhaiskasvatussuhdeAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'varhaiskasvatuspaatos',)
    search_fields = ('=id', '=varhaiskasvatuspaatos__id',)
    raw_id_fields = ('toimipaikka', 'varhaiskasvatuspaatos',)


class HuoltajaAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'get_henkilo_oid',)
    search_fields = ('=id', '=henkilo__henkilo_oid',)
    raw_id_fields = ('henkilo',)

    @display(ordering='henkilo__henkilo_oid', description='henkilo_oid')
    def get_henkilo_oid(self, instance):
        return instance.henkilo.henkilo_oid


class HuoltajuussuhdeAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'huoltaja',)
    search_fields = ('=id', '=huoltaja__id',)
    raw_id_fields = ('lapsi', 'huoltaja',)


class MaksutietoAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'get_lapsi',)
    search_fields = ('=id', '=huoltajuussuhteet__lapsi__id',)

    @display(ordering='huoltajuussuhteet__lapsi__id', description='lapsi')
    def get_lapsi(self, instance):
        return instance.huoltajuussuhteet.first().lapsi.id


class MaksutietoHuoltajuussuhdeAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'maksutieto', 'huoltajuussuhde',)
    search_fields = ('=id', '=maksutieto__id', '=huoltajuussuhde__id',)
    raw_id_fields = ('maksutieto', 'huoltajuussuhde',)


class PaosToimintaAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'get_oma_organisaatio_oid', 'get_paos_organisaatio_oid', 'get_paos_toimipaikka_oid',)
    search_fields = ('=id', '=oma_organisaatio__organisaatio_oid', '=paos_organisaatio__organisaatio_oid',
                     '=paos_toimipaikka__organisaatio_oid',)
    raw_id_fields = ('oma_organisaatio', 'paos_organisaatio', 'paos_toimipaikka',)

    @display(ordering='oma_organisaatio__organisaatio_oid', description='oma_organisaatio organisaatio_oid')
    def get_oma_organisaatio_oid(self, instance):
        return getattr(instance.oma_organisaatio, 'organisaatio_oid', None)

    @display(ordering='paos_organisaatio__organisaatio_oid', description='paos_organisaatio organisaatio_oid')
    def get_paos_organisaatio_oid(self, instance):
        return getattr(instance.paos_organisaatio, 'organisaatio_oid', None)

    @display(ordering='paos_toimipaikka__organisaatio_oid', description='paos_toimipaikka organisaatio_oid')
    def get_paos_toimipaikka_oid(self, instance):
        return getattr(instance.paos_toimipaikka, 'organisaatio_oid', None)


class PaosOikeusAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'get_jarjestaja_kunta_organisaatio_oid', 'get_tuottaja_organisaatio_oid',)
    search_fields = ('=id', '=jarjestaja_kunta_organisaatio__organisaatio_oid',
                     '=tuottaja_organisaatio__organisaatio_oid',)
    raw_id_fields = ('jarjestaja_kunta_organisaatio', 'tuottaja_organisaatio', 'tallentaja_organisaatio',)

    @display(ordering='jarjestaja_kunta_organisaatio__organisaatio_oid',
             description='jarjestaja_kunta_organisaatio organisaatio_oid')
    def get_jarjestaja_kunta_organisaatio_oid(self, instance):
        return instance.jarjestaja_kunta_organisaatio.organisaatio_oid

    @display(ordering='tuottaja_organisaatio__organisaatio_oid', description='tuottaja_organisaatio organisaatio_oid')
    def get_tuottaja_organisaatio_oid(self, instance):
        return instance.tuottaja_organisaatio.organisaatio_oid


class TyontekijaAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'get_henkilo_oid', 'get_vakajarjestaja_oid',)
    search_fields = ('=id', '=vakajarjestaja__organisaatio_oid', '=henkilo__henkilo_oid',)
    raw_id_fields = ('henkilo', 'vakajarjestaja',)

    @display(ordering='henkilo__henkilo_oid', description='henkilo_oid')
    def get_henkilo_oid(self, instance):
        return instance.henkilo.henkilo_oid

    @display(ordering='vakajarjestaja__organisaatio_oid', description='vakajarjestaja organisaatio_oid')
    def get_vakajarjestaja_oid(self, instance):
        return instance.vakajarjestaja.organisaatio_oid


class TutkintoAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'get_henkilo_oid', 'get_vakajarjestaja_oid',)
    search_fields = ('=id', '=vakajarjestaja__organisaatio_oid', '=henkilo__henkilo_oid',)
    raw_id_fields = ('henkilo', 'vakajarjestaja',)

    @display(ordering='henkilo__henkilo_oid', description='henkilo_oid')
    def get_henkilo_oid(self, instance):
        return instance.henkilo.henkilo_oid

    @display(ordering='vakajarjestaja__organisaatio_oid', description='vakajarjestaja organisaatio_oid')
    def get_vakajarjestaja_oid(self, instance):
        return instance.vakajarjestaja.organisaatio_oid


class PalvelussuhdeAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'tyontekija',)
    search_fields = ('=id', '=tyontekija__id',)
    raw_id_fields = ('tyontekija',)


class TyoskentelypaikkaAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'palvelussuhde', 'get_toimipaikka_organisaatio_oid',)
    search_fields = ('=id', '=palvelussuhde__id', '=toimipaikka__organisaatio_oid',)
    raw_id_fields = ('palvelussuhde', 'toimipaikka',)

    @display(ordering='toimipaikka__organisaatio_oid', description='toimipaikka organisaatio_oid')
    def get_toimipaikka_organisaatio_oid(self, instance):
        return getattr(instance.toimipaikka, 'organisaatio_oid', None)


class PidempipoissaoloAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'palvelussuhde',)
    search_fields = ('=id', '=palvelussuhde__id',)
    raw_id_fields = ('palvelussuhde',)


class TaydennyskoulutusAdmin(AdminWithGuardianAndHistory):
    pass


class TaydennyskoulutusTyontekijaAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'taydennyskoulutus', 'tyontekija',)
    search_fields = ('=id', '=taydennyskoulutus__id', '=tyontekija__id',)
    raw_id_fields = ('taydennyskoulutus', 'tyontekija',)


class TilapainenHenkilostoAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'get_vakajarjestaja_oid',)
    search_fields = ('=id', '=vakajarjestaja__organisaatio_oid',)
    raw_id_fields = ('vakajarjestaja',)

    @display(ordering='vakajarjestaja__organisaatio_oid', description='vakajarjestaja organisaatio_oid')
    def get_vakajarjestaja_oid(self, instance):
        return instance.vakajarjestaja.organisaatio_oid


class BatchErrorAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'henkilo',)
    search_fields = ('=id', '=henkilo__id',)
    raw_id_fields = ('henkilo',)


class AuthUserAdmin(ModelAdmin):
    list_display = ('id', 'username', 'email',)
    search_fields = ('=id', 'username', 'email',)
    # Override fieldsets to include description about password-field
    fieldsets = (
        (None, {
            'fields': ('last_login', 'is_superuser', 'groups', 'user_permissions', 'username', 'first_name',
                       'last_name', 'email', 'is_staff', 'is_active', 'date_joined',)
        }),
        ('Password', {
            'fields': ('password',),
            'description': 'To set password as blank string (no password, cannot login with password so only via CAS), '
                           'enter a single hyphen (-)'
        })
    )

    def save_model(self, request, obj, form, change):
        # Allow setting blank string value to password-field in Admin-form by inputting a hyphen (-)
        # It is very difficult to override field validations (would need to override SimpleArrayField clean-method)
        if obj.password == '-':
            obj.password = ''
        return super().save_model(request, obj, form, change)


class LoginCertificateAdmin(AdminWithGuardianAndHistory):
    list_display = ('id', 'get_organisaatio_oid', 'api_path',)
    search_fields = ('=id', '=organisaatio__organisaatio_oid', 'api_path',)
    raw_id_fields = ('user', 'organisaatio',)

    @display(ordering='organisaatio__organisaatio_oid', description='organisaatio_oid')
    def get_organisaatio_oid(self, instance):
        return getattr(instance.organisaatio, 'organisaatio_oid', None)


class Z3_AdditionalCasUserFieldsAdmin(ModelAdmin):
    list_display = ('user_id', 'user',)
    search_fields = ('=user__id', 'user__username',)
    raw_id_fields = ('user',)


class Z7_AdditionalUserFieldsAdmin(ModelAdmin):
    list_display = ('user_id', 'user',)
    search_fields = ('=user__id', 'user__username',)
    raw_id_fields = ('user',)


admin.site.unregister(User)

admin.site.register(User, AuthUserAdmin)
admin.site.register(Organisaatio, OrganisaatioAdmin)
admin.site.register(Toimipaikka, ToimipaikkaAdmin)
admin.site.register(ToiminnallinenPainotus, ToiminnallinenPainotusAdmin)
admin.site.register(KieliPainotus, KieliPainotusAdmin)
admin.site.register(Henkilo, HenkiloAdmin)
admin.site.register(Lapsi, LapsiAdmin)
admin.site.register(Huoltaja, HuoltajaAdmin)
admin.site.register(Huoltajuussuhde, HuoltajuussuhdeAdmin)
admin.site.register(Varhaiskasvatuspaatos, VarhaiskasvatuspaatosAdmin)
admin.site.register(Varhaiskasvatussuhde, VarhaiskasvatussuhdeAdmin)
admin.site.register(Maksutieto, MaksutietoAdmin)
admin.site.register(MaksutietoHuoltajuussuhde, MaksutietoHuoltajuussuhdeAdmin)
admin.site.register(PaosToiminta, PaosToimintaAdmin)
admin.site.register(PaosOikeus, PaosOikeusAdmin)
admin.site.register(Tyontekija, TyontekijaAdmin)
admin.site.register(TilapainenHenkilosto, TilapainenHenkilostoAdmin)
admin.site.register(Tutkinto, TutkintoAdmin)
admin.site.register(Palvelussuhde, PalvelussuhdeAdmin)
admin.site.register(Tyoskentelypaikka, TyoskentelypaikkaAdmin)
admin.site.register(PidempiPoissaolo, PidempipoissaoloAdmin)
admin.site.register(Taydennyskoulutus, TaydennyskoulutusAdmin)
admin.site.register(TaydennyskoulutusTyontekija, TaydennyskoulutusTyontekijaAdmin)
admin.site.register(YearlyReportSummary, AdminWithGuardianAndHistory)
admin.site.register(Aikaleima, AdminWithGuardianAndHistory)
admin.site.register(BatchError, BatchErrorAdmin)
admin.site.register(LoginCertificate, LoginCertificateAdmin)
admin.site.register(Z3_AdditionalCasUserFields, Z3_AdditionalCasUserFieldsAdmin)
admin.site.register(Z7_AdditionalUserFields, Z7_AdditionalUserFieldsAdmin)
