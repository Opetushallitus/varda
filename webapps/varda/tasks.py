import os

from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db.models import Q
from guardian.models import UserObjectPermission, GroupObjectPermission
from guardian.utils import clean_orphan_obj_perms

from varda import oppijanumerorekisteri
from varda import organisaatiopalvelu
from varda import permissions
from varda import permission_groups
from varda.audit_log import audit_log


def pod_ordinal_index_is_zero():
    splitted_hostname = os.environ["HOSTNAME"].split("-")
    if len(splitted_hostname) == 2:
        pod_ordinal_index = splitted_hostname[1]  # e.g. varda-0 --> 0
        if pod_ordinal_index == "0":
            return True
    return False


def pod_ordinal_index_is_one():
    splitted_hostname = os.environ["HOSTNAME"].split("-")
    if len(splitted_hostname) == 2:
        pod_ordinal_index = splitted_hostname[1]
        if pod_ordinal_index == "1":
            return True
    return False


def pod_ordinal_index_is_two():
    splitted_hostname = os.environ["HOSTNAME"].split("-")
    if len(splitted_hostname) == 2:
        pod_ordinal_index = splitted_hostname[1]
        if pod_ordinal_index == "2":
            return True
    return False


# This is currently only needed for testing, don't remove!
@shared_task
def add(x, y):
    return x + y


@shared_task
def run_management_commands(periodic_task=False):
    """
    To be run periodically, e.g. to clean out expired sessions
    """
    if not periodic_task or pod_ordinal_index_is_zero():
        call_command('clearsessions', verbosity=0)
        call_command('django_cas_ng_clean_sessions', verbosity=0)


@shared_task
def remove_all_auth_tokens(periodic_task=False):
    from rest_framework.authtoken.models import Token
    if not periodic_task or pod_ordinal_index_is_zero():
        Token.objects.all().delete()


@shared_task
def update_vakajarjestajat(periodic_task=False):
    if not periodic_task or pod_ordinal_index_is_zero():
        organisaatiopalvelu.fetch_organisaatio_info()


@shared_task
def update_henkilot_without_oid(periodic_task=False):
    if not periodic_task or pod_ordinal_index_is_zero():
        oppijanumerorekisteri.fetch_henkilot_without_oid()


@shared_task
def update_oph_staff_to_vakajarjestaja_groups(periodic_task=False):
    if not periodic_task or pod_ordinal_index_is_zero():
        permission_groups.add_oph_staff_to_vakajarjestaja_katselija_groups()


@shared_task
def update_modified_henkilot(periodic_task=False):
    if not periodic_task or pod_ordinal_index_is_zero():
        oppijanumerorekisteri.fetch_and_update_modified_henkilot()


@shared_task
def update_toimipaikat_in_organisaatiopalvelu_task(periodic_task=False):
    if not periodic_task or pod_ordinal_index_is_zero():
        organisaatiopalvelu.update_toimipaikat_in_organisaatiopalvelu()


@shared_task
def update_henkilo_data_by_oid(henkilo_id, henkilo_oid):
    oppijanumerorekisteri.fetch_henkilo_data_by_oid(henkilo_id, henkilo_oid)


@shared_task
def update_henkilot_with_oid():
    oppijanumerorekisteri.fetch_henkilot_with_oid()


@shared_task
def fetch_huoltajat_task(periodic_task=False):
    if not periodic_task or pod_ordinal_index_is_two():
        oppijanumerorekisteri.fetch_huoltajat()


@shared_task
def fetch_lapsen_huoltajat_task(lapsi_id):
    oppijanumerorekisteri.fetch_lapsen_huoltajat(lapsi_id)


@shared_task
def update_all_organisaatio_service_originated_organisations_task(periodic_task=False):
    """
    Updates all organisations which data is managed by organisaatio service
    :return: None
    """
    if not periodic_task or pod_ordinal_index_is_zero():
        organisaatiopalvelu.update_all_organisaatio_service_organisations()


@shared_task
def update_huoltajasuhteet_task(periodic_task=False):
    """
    Updates huoltajasuhde changes from oppijanumerorekisteri
    :param periodic_task:
    :return: None
    """
    if not periodic_task or pod_ordinal_index_is_zero():
        oppijanumerorekisteri.update_huoltajuussuhteet()


@shared_task
def send_audit_log_to_aws_task(periodic_task=False):
    if not periodic_task or pod_ordinal_index_is_one():
        audit_log.collect_audit_log_and_send_to_aws()


@shared_task
def guardian_clean_orphan_objects(periodic_task=False):
    if not periodic_task or pod_ordinal_index_is_one():
        clean_orphan_obj_perms()


@shared_task
def change_paos_tallentaja_organization_task(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id,
                                             tallentaja_organisaatio_id, voimassa_kytkin):
    permissions.change_paos_tallentaja_organization(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id,
                                                    tallentaja_organisaatio_id, voimassa_kytkin)


@shared_task
def delete_object_permissions_explicitly_task(content_type_id, instance_id):
    """
    Object permissions need to be deleted explicitly:
    https://django-guardian.readthedocs.io/en/stable/userguide/caveats.html
    """
    content_type = ContentType.objects.get(id=content_type_id)
    filters = Q(content_type=content_type, object_pk=str(instance_id))
    UserObjectPermission.objects.filter(filters).delete()
    GroupObjectPermission.objects.filter(filters).delete()
