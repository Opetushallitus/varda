from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db.models import Q
from guardian.models import UserObjectPermission, GroupObjectPermission

from varda import oppijanumerorekisteri, koodistopalvelu
from varda import organisaatiopalvelu
from varda import permission_groups
from varda import permissions
from varda.audit_log import audit_log
from varda.models import Henkilo, Taydennyskoulutus
from varda.permission_groups import assign_object_permissions_to_taydennyskoulutus_groups


@shared_task
def add(x, y):
    """
    This is currently only needed for testing, don't remove!
    """
    return x + y


"""
Use acks_late=True for the task-decoration, unless periodic task which always gets called with the same arguments.
"""


@shared_task
def run_management_commands():
    """
    To be run periodically, e.g. to clean out expired sessions
    """
    call_command('clearsessions', verbosity=0)
    call_command('django_cas_ng_clean_sessions', verbosity=0)


@shared_task(acks_late=True)
def remove_all_auth_tokens():
    from rest_framework.authtoken.models import Token
    Token.objects.all().delete()


@shared_task
def update_oph_staff_to_vakajarjestaja_groups():
    permission_groups.add_oph_staff_to_vakajarjestaja_katselija_groups()


@shared_task
def update_vakajarjestajat():
    organisaatiopalvelu.fetch_organisaatio_info()


@shared_task
def update_modified_henkilot():
    oppijanumerorekisteri.fetch_and_update_modified_henkilot()


@shared_task
def update_toimipaikat_in_organisaatiopalvelu_task():
    organisaatiopalvelu.update_toimipaikat_in_organisaatiopalvelu()


@shared_task
def fetch_huoltajat_task():
    oppijanumerorekisteri.fetch_huoltajat()


@shared_task
def update_all_organisaatio_service_originated_organisations_task():
    """
    Updates all organisations which data is managed by organisaatio service
    :return: None
    """
    organisaatiopalvelu.update_all_organisaatio_service_organisations()


@shared_task(acks_late=True)
def update_henkilot_with_oid():
    oppijanumerorekisteri.fetch_henkilot_with_oid()


@shared_task(acks_late=True)
def update_henkilo_data_by_oid(henkilo_oid, henkilo_id, is_fetch_huoltajat=False):
    oppijanumerorekisteri.fetch_henkilo_data_by_oid(henkilo_oid, henkilo_id)
    if is_fetch_huoltajat:
        oppijanumerorekisteri.update_huoltajuussuhde(henkilo_oid)


@shared_task
def update_huoltajasuhteet_task():
    """
    Updates huoltajasuhde changes from oppijanumerorekisteri
    :return: None
    """
    oppijanumerorekisteri.update_huoltajuussuhteet()


@shared_task
def send_audit_log_to_aws_task():
    audit_log.collect_audit_log_and_send_to_aws()


@shared_task
def guardian_clean_orphan_objects():
    # from guardian.utils import clean_orphan_obj_perms
    # clean_orphan_obj_perms() - We do not want to run this currently.
    pass


@shared_task(acks_late=True)
def change_paos_tallentaja_organization_task(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id,
                                             tallentaja_organisaatio_id, voimassa_kytkin):
    permissions.change_paos_tallentaja_organization(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id,
                                                    tallentaja_organisaatio_id, voimassa_kytkin)


@shared_task(acks_late=True)
def delete_object_permissions_explicitly_task(content_type_id, instance_id):
    """
    Object permissions need to be deleted explicitly:
    https://django-guardian.readthedocs.io/en/stable/userguide/caveats.html
    """
    content_type = ContentType.objects.get(id=content_type_id)
    filters = Q(content_type=content_type, object_pk=str(instance_id))
    UserObjectPermission.objects.filter(filters).delete()
    GroupObjectPermission.objects.filter(filters).delete()


@shared_task
def update_koodistot_task():
    koodistopalvelu.update_koodistot()


@shared_task
def remove_address_information_from_tyontekijat_only_task():
    henkilot = Henkilo.objects.filter(~Q(kotikunta_koodi='') | ~Q(katuosoite='') |
                                      ~Q(postinumero='') | ~Q(postitoimipaikka=''),
                                      huoltaja__isnull=True, tyontekijat__isnull=False).distinct()

    # Loop through each Henkilo so that save signals are processed correctly
    for henkilo in henkilot:
        henkilo.remove_address_information()
        henkilo.save()


@shared_task(acks_late=True)
def assign_taydennyskoulutus_permissions_for_toimipaikka_task(vakajarjestaja_oid, toimipaikka_oid):
    """
    Assign object level permissions to all taydennyskoulutukset of given vakajarjestaja for toimipaikka level groups
    :param vakajarjestaja_oid: OID of vakajarjestaja
    :param toimipaikka_oid: OID of toimipaikka
    """
    taydennyskoulutukset = Taydennyskoulutus.objects.filter(tyontekijat__vakajarjestaja__organisaatio_oid=vakajarjestaja_oid)
    [assign_object_permissions_to_taydennyskoulutus_groups(toimipaikka_oid, Taydennyskoulutus, taydennyskoulutus)
     for taydennyskoulutus in taydennyskoulutukset
     ]
