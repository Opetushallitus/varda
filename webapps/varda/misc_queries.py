from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Q

from varda.models import PaosOikeus, PaosToiminta, Toimipaikka, Z9_RelatedObjectChanged


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


def get_related_object_changed_id_qs(model_name, datetime_gt, datetime_lte, additional_filters=None,
                                     return_value='instance_id'):
    additional_filters = additional_filters or {}
    return (Z9_RelatedObjectChanged.objects
            .values('model_name', 'instance_id', 'trigger_model_name', 'trigger_instance_id')
            .filter(model_name=model_name, changed_timestamp__gt=datetime_gt, changed_timestamp__lte=datetime_lte,
                    **additional_filters)
            .annotate(history_type_list=StringAgg('history_type', ','))
            .filter(~(Q(history_type_list__contains='+') & Q(history_type_list__contains='-')))
            .values_list(return_value, flat=True).distinct())
