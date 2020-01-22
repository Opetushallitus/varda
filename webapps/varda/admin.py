from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import (VakaJarjestaja, Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Henkilo,
                     Maksutieto, Huoltajuussuhde, Tyontekija, Taydennyskoulutus, Ohjaajasuhde, Lapsi, Huoltaja,
                     Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Aikaleima, PaosToiminta, PaosOikeus)


class AdminWithGuardianAndHistory(GuardedModelAdmin, SimpleHistoryAdmin):
    pass


admin.site.register(VakaJarjestaja, AdminWithGuardianAndHistory)
admin.site.register(Toimipaikka, AdminWithGuardianAndHistory)
admin.site.register(ToiminnallinenPainotus, AdminWithGuardianAndHistory)
admin.site.register(KieliPainotus, AdminWithGuardianAndHistory)
admin.site.register(Henkilo, AdminWithGuardianAndHistory)
admin.site.register(Tyontekija, AdminWithGuardianAndHistory)
admin.site.register(Taydennyskoulutus, AdminWithGuardianAndHistory)
admin.site.register(Ohjaajasuhde, AdminWithGuardianAndHistory)
admin.site.register(Lapsi, AdminWithGuardianAndHistory)
admin.site.register(Huoltaja, AdminWithGuardianAndHistory)
admin.site.register(Huoltajuussuhde, AdminWithGuardianAndHistory)
admin.site.register(Varhaiskasvatuspaatos, AdminWithGuardianAndHistory)
admin.site.register(Varhaiskasvatussuhde, AdminWithGuardianAndHistory)
admin.site.register(Maksutieto, AdminWithGuardianAndHistory)
admin.site.register(Aikaleima, AdminWithGuardianAndHistory)
admin.site.register(PaosToiminta, AdminWithGuardianAndHistory)
admin.site.register(PaosOikeus, AdminWithGuardianAndHistory)
