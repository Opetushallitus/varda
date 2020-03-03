from django.db.models import Q
from varda.models import Toimipaikka, PaosOikeus, PaosToiminta


def get_paos_toimipaikat(vakajarjestaja_obj, is_only_active_paostoiminta_included=True):
    tuottaja_organization_ids = (PaosOikeus
                                 .objects
                                 .filter(jarjestaja_kunta_organisaatio=vakajarjestaja_obj)
                                 .values_list('tuottaja_organisaatio__id', flat=True))

    tuottaja_organizations_toimipaikka_ids = (Toimipaikka
                                              .objects
                                              .filter(vakajarjestaja__id__in=tuottaja_organization_ids)
                                              .values_list('id', flat=True))
    paostoiminta_condition = Q(oma_organisaatio=vakajarjestaja_obj) & Q(paos_toimipaikka__id__in=tuottaja_organizations_toimipaikka_ids)
    if is_only_active_paostoiminta_included:
        paostoiminta_condition = paostoiminta_condition & Q(voimassa_kytkin=True)
    return (PaosToiminta
            .objects
            .filter(paostoiminta_condition)
            .values_list('paos_toimipaikka', flat=True))
