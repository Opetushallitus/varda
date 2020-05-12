from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import (Aikaleima, BatchError, Henkilo, Huoltaja, Huoltajuussuhde, KieliPainotus, Lapsi, Maksutieto,
                     PaosOikeus, PaosToiminta, TilapainenHenkilosto, ToiminnallinenPainotus, Toimipaikka, Tutkinto,
                     Tyontekija, VakaJarjestaja, Varhaiskasvatuspaatos, Varhaiskasvatussuhde,)


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


class PaosToimintaAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('oma_organisaatio', 'paos_organisaatio', 'paos_toimipaikka', )


class TilapainenHenkilostoAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('vakajarjestaja', )


class TutkintoAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ('henkilo', )


admin.site.register(VakaJarjestaja, AdminWithGuardianAndHistory)
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
admin.site.register(BatchError, AdminWithGuardianAndHistory)
admin.site.register(PaosToiminta, PaosToimintaAdmin)
admin.site.register(PaosOikeus, AdminWithGuardianAndHistory)
admin.site.register(Tyontekija, AdminWithGuardianAndHistory)
admin.site.register(TilapainenHenkilosto, TilapainenHenkilostoAdmin)
admin.site.register(Tutkinto, TutkintoAdmin)
