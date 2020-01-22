from django.db.models import Q
from varda.models import Toimipaikka, PaosOikeus, PaosToiminta


def get_paos_toimipaikat(vakajarjestaja_obj):
    tuottaja_organization_ids = (PaosOikeus
                                 .objects
                                 .filter(jarjestaja_kunta_organisaatio=vakajarjestaja_obj)
                                 .values_list('tuottaja_organisaatio__id', flat=True))

    tuottaja_organizations_toimipaikka_ids = (Toimipaikka
                                              .objects
                                              .filter(vakajarjestaja__id__in=tuottaja_organization_ids)
                                              .values_list('id', flat=True))

    return (PaosToiminta
            .objects
            .filter(
                Q(oma_organisaatio=vakajarjestaja_obj) &
                Q(paos_toimipaikka__id__in=tuottaja_organizations_toimipaikka_ids))
            .values_list('paos_toimipaikka', flat=True))
