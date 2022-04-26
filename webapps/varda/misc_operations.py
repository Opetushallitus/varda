import logging

from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from varda.enums.error_messages import ErrorMessages
from varda.enums.hallinnointijarjestelma import Hallinnointijarjestelma
from varda.models import (KieliPainotus, Maksutieto, Palvelussuhde, ToiminnallinenPainotus, Toimipaikka,
                          Tyoskentelypaikka, Varhaiskasvatuspaatos, Varhaiskasvatussuhde)

logger = logging.getLogger(__name__)


def save_paattymis_pvm(instance, paattymis_pvm):
    if instance.alkamis_pvm > paattymis_pvm:
        logger.error(f'Could not update paattymis_pvm for {instance._meta.model.__name__} with id {instance.id}.')
        raise ValidationError({'paattymis_pvm': [ErrorMessages.MI004.value]})
    instance.paattymis_pvm = paattymis_pvm
    instance.save()


def set_paattymis_pvm_for_vakajarjestaja_data(vakajarjestaja, paattymis_pvm):
    """
    This function is used to set paattymis_pvm for Toimipaikka, KieliPainotus, ToiminnallinenPainotus,
    Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Maksutieto, Palvelussuhde and Tyoskentelypaikka of provided
    Organisaatio. paattymis_pvm is modified if it is None or it is after the provided paattymis_pvm.
    Data of PAOS Lapsi objects is not modified.
    :param vakajarjestaja: Organisaatio object
    :param paattymis_pvm: Date
    :return: dict, number of modified objects per model
    """
    paattymis_pvm_filter = Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gt=paattymis_pvm)
    painotus_filter = (Q(toimipaikka__vakajarjestaja=vakajarjestaja) &
                       Q(toimipaikka__hallinnointijarjestelma=Hallinnointijarjestelma.VARDA.value))

    with transaction.atomic():
        qs_list = [Toimipaikka.objects.filter(Q(vakajarjestaja=vakajarjestaja) &
                                              Q(hallinnointijarjestelma=Hallinnointijarjestelma.VARDA.value) &
                                              paattymis_pvm_filter),
                   KieliPainotus.objects.filter(painotus_filter & paattymis_pvm_filter),
                   ToiminnallinenPainotus.objects.filter(painotus_filter & paattymis_pvm_filter),
                   Varhaiskasvatuspaatos.objects.filter(Q(lapsi__vakatoimija=vakajarjestaja) & paattymis_pvm_filter),
                   Varhaiskasvatussuhde.objects.filter(Q(varhaiskasvatuspaatos__lapsi__vakatoimija=vakajarjestaja) &
                                                       paattymis_pvm_filter),
                   Maksutieto.objects.filter(Q(huoltajuussuhteet__lapsi__vakatoimija=vakajarjestaja) &
                                             paattymis_pvm_filter).distinct('id'),
                   Palvelussuhde.objects.filter(Q(tyontekija__vakajarjestaja=vakajarjestaja) &
                                                paattymis_pvm_filter),
                   Tyoskentelypaikka.objects.filter(Q(palvelussuhde__tyontekija__vakajarjestaja=vakajarjestaja) &
                                                    paattymis_pvm_filter)]

        result_dict = {}
        for qs in qs_list:
            index = 0
            for instance in qs.iterator():
                save_paattymis_pvm(instance, paattymis_pvm)
                index += 1
            result_dict[qs.model.get_name()] = index
        return result_dict
