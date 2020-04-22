from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import (Aikaleima, BatchError, Henkilo, Huoltaja, Huoltajuussuhde, KieliPainotus, Lapsi, Maksutieto,
                     PaosOikeus, PaosToiminta, ToiminnallinenPainotus, Toimipaikka, Tyontekija, VakaJarjestaja,
                     Varhaiskasvatuspaatos, Varhaiskasvatussuhde,)


class AdminWithGuardianAndHistory(GuardedModelAdmin, SimpleHistoryAdmin):
    pass


class HuoltajuussuhdeAdmin(AdminWithGuardianAndHistory):
    raw_id_fields = ("lapsi", "huoltaja", )


admin.site.register(VakaJarjestaja, AdminWithGuardianAndHistory)
admin.site.register(Toimipaikka, AdminWithGuardianAndHistory)
admin.site.register(ToiminnallinenPainotus, AdminWithGuardianAndHistory)
admin.site.register(KieliPainotus, AdminWithGuardianAndHistory)
admin.site.register(Henkilo, AdminWithGuardianAndHistory)
admin.site.register(Lapsi, AdminWithGuardianAndHistory)
admin.site.register(Huoltaja, AdminWithGuardianAndHistory)
admin.site.register(Huoltajuussuhde, HuoltajuussuhdeAdmin)
admin.site.register(Varhaiskasvatuspaatos, AdminWithGuardianAndHistory)
admin.site.register(Varhaiskasvatussuhde, AdminWithGuardianAndHistory)
admin.site.register(Maksutieto, AdminWithGuardianAndHistory)
admin.site.register(Aikaleima, AdminWithGuardianAndHistory)
admin.site.register(BatchError, AdminWithGuardianAndHistory)
admin.site.register(PaosToiminta, AdminWithGuardianAndHistory)
admin.site.register(PaosOikeus, AdminWithGuardianAndHistory)
admin.site.register(Tyontekija, AdminWithGuardianAndHistory)
