from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.auth.models import User
from guardian.admin import GuardedModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import (Aikaleima, BatchError, Henkilo, Huoltaja, Huoltajuussuhde, KieliPainotus, Lapsi, Maksutieto,
                     Tyoskentelypaikka, Palvelussuhde, PaosOikeus, PaosToiminta, TilapainenHenkilosto,
                     ToiminnallinenPainotus, Toimipaikka, Tutkinto, Tyontekija, VakaJarjestaja, Varhaiskasvatuspaatos,
                     Varhaiskasvatussuhde, PidempiPoissaolo, Taydennyskoulutus)


class AdminWithGuardianAndHistory(GuardedModelAdmin, SimpleHistoryAdmin):
    pass


class HuoltajuussuhdeAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('lapsi', 'huoltaja', 'maksutiedot', )


class LapsiAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('henkilo', )


class HuoltajaAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('henkilo', )


class VarhaiskasvatuspaatosAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('lapsi', )


class VarhaiskasvatussuhdeAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('toimipaikka', 'varhaiskasvatuspaatos', )


class ToiminnallinenPainotusAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('toimipaikka', )


class KieliPainotusAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('toimipaikka', )


class BatchErrorAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('henkilo', )


class PaosToimintaAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('oma_organisaatio', 'paos_organisaatio', 'paos_toimipaikka', )


class TyontekijaAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('henkilo', 'vakajarjestaja', )


class TilapainenHenkilostoAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('vakajarjestaja', )


class TutkintoAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('henkilo', )


class PalvelussuhdeAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('tyontekija', )


class TyoskentelypaikkaAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('palvelussuhde', 'toimipaikka', )


class AuthUserAdmin(ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', )
    search_fields = ('username', )


class PidempipoissaoloAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('palvelussuhde', )


class TaydennyskoulutusAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('tyontekijat', )


class VakajarjestajaAdmin(AdminWithGuardianAndHistory):
    # Override fieldsets to include description about integraatio_organisaatio-field
    fieldsets = (
        (None, {
            'fields': ('nimi', 'y_tunnus', 'organisaatio_oid', 'kunta_koodi', 'sahkopostiosoite', 'ipv4_osoitteet',
                       'ipv6_osoitteet', 'kayntiosoite', 'kayntiosoite_postinumero', 'kayntiosoite_postitoimipaikka',
                       'postiosoite', 'postinumero', 'postitoimipaikka', 'puhelinnumero', 'ytjkieli', 'yritysmuoto',
                       'alkamis_pvm', 'paattymis_pvm', 'changed_by',)
        }), ('Integration flags', {
            'fields': ('integraatio_organisaatio',),
            'description': 'To clear all integration flags, enter a single hyphen (-)'
        }),
    )

    def save_model(self, request, obj, form, change):
        # Allow clearing integraatio_organisaatio-field in Admin-form by inputting a hyphen (-)
        # It is very difficult to override field validations (would need to override SimpleArrayField clean-method)
        if obj.integraatio_organisaatio == ['-']:
            obj.integraatio_organisaatio = []
        return super(VakajarjestajaAdmin, self).save_model(request, obj, form, change)


admin.site.unregister(User)

admin.site.register(User, AuthUserAdmin)
admin.site.register(VakaJarjestaja, VakajarjestajaAdmin)
admin.site.register(Toimipaikka, AdminWithGuardianAndHistory)
admin.site.register(ToiminnallinenPainotus, ToiminnallinenPainotusAdmin)
admin.site.register(KieliPainotus, KieliPainotusAdmin)
admin.site.register(Henkilo, AdminWithGuardianAndHistory)
admin.site.register(Lapsi, LapsiAdmin)
admin.site.register(Huoltaja, HuoltajaAdmin)
admin.site.register(Huoltajuussuhde, HuoltajuussuhdeAdmin)
admin.site.register(Varhaiskasvatuspaatos, VarhaiskasvatuspaatosAdmin)
admin.site.register(Varhaiskasvatussuhde, VarhaiskasvatussuhdeAdmin)
admin.site.register(Maksutieto, AdminWithGuardianAndHistory)
admin.site.register(Aikaleima, AdminWithGuardianAndHistory)
admin.site.register(BatchError, BatchErrorAdmin)
admin.site.register(PaosToiminta, PaosToimintaAdmin)
admin.site.register(PaosOikeus, AdminWithGuardianAndHistory)
admin.site.register(Tyontekija, TyontekijaAdmin)
admin.site.register(TilapainenHenkilosto, TilapainenHenkilostoAdmin)
admin.site.register(Tutkinto, TutkintoAdmin)
admin.site.register(Palvelussuhde, PalvelussuhdeAdmin)
admin.site.register(Tyoskentelypaikka, TyoskentelypaikkaAdmin)
admin.site.register(PidempiPoissaolo, PidempipoissaoloAdmin)
admin.site.register(Taydennyskoulutus, TaydennyskoulutusAdmin)
