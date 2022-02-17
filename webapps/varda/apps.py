import os
from functools import partial

from django.apps import AppConfig
from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_migrate, post_save, pre_delete, pre_save
from django.utils import timezone

from varda.constants import ALIVE_BOOT_TIME_CACHE_KEY, ALIVE_SEQ_CACHE_KEY
from varda.migrations.production.setup import (clear_old_permissions, create_henkilosto_template_groups,
                                               create_huoltajatiedot_template_groups, create_oph_luovutuspalvelu_group,
                                               create_paos_template_groups, create_raportit_template_groups,
                                               create_toimijatiedot_template_groups, load_initial_data)
from varda.migrations.testing.setup import (create_initial_koodisto_data, create_postinumero_koodisto_data,
                                            create_virhe_koodisto_data, create_yritysmuoto_koodisto_data,
                                            load_testing_data)


def run_post_migration_tasks(sender, **kwargs):
    if 'plan' in kwargs:
        """
        Example:

        plan = [
        (<Migration contenttypes.0001_initial>, False),
        (<Migration auth.0001_initial>, False),
        (<Migration admin.0001_initial>, False),
        (<Migration admin.0002_logentry_remove_auto_add>, False),
        (<Migration admin.0003_logentry_add_action_flag_choices>, False),
        (<Migration contenttypes.0002_remove_content_type_name>, False),
        (<Migration auth.0002_alter_permission_name_max_length>, False),
        (<Migration auth.0003_alter_user_email_max_length>, False),
        (<Migration auth.0004_alter_user_username_opts>, False),
        (<Migration auth.0005_alter_user_last_login_null>, False),
        (<Migration auth.0006_require_contenttypes_0002>, False),
        (<Migration auth.0007_alter_validators_add_error_messages>, False),
        (<Migration auth.0008_alter_user_username_max_length>, False),
        (<Migration auth.0009_alter_user_last_name_max_length>, False),
        (<Migration authtoken.0001_initial>, False),
        (<Migration authtoken.0002_auto_20160226_1747>, False),
        (<Migration django_cas_ng.0001_initial>, False),
        (<Migration django_celery_beat.0001_initial>, False),
        (<Migration django_celery_beat.0002_auto_20161118_0346>, False),
        (<Migration django_celery_beat.0003_auto_20161209_0049>, False),
        (<Migration django_celery_beat.0004_auto_20170221_0000>, False),
        (<Migration django_celery_beat.0005_add_solarschedule_events_choices_squashed_0009_merge_20181012_1416>, False),
        (<Migration django_celery_beat.0006_periodictask_priority>, False),
        (<Migration django_celery_results.0001_initial>, False),
        (<Migration django_celery_results.0002_add_task_name_args_kwargs>, False),
        (<Migration django_celery_results.0003_auto_20181106_1101>, False),
        (<Migration guardian.0001_initial>, False),
        (<Migration sessions.0001_initial>, False),
        (<Migration sites.0001_initial>, False),
        (<Migration sites.0002_alter_domain_unique>, False),
        (<Migration varda.0001_initial>, False),
        (<Migration varda.0002_auto_20190131_1550>, False),
        (<Migration varda.0003_auto_20190201_1429>, False)]

        Boolean-value in the tuple tells:
        False: Migration was applied
        True: Migration was rolled back
        """
        migration_action_dict = {
            '0001_initial': [load_initial_data],
            '0010_auto_20190807_1055': [create_huoltajatiedot_template_groups],
            '0012_auto_20191031_0926': [create_paos_template_groups, clear_old_permissions],
            '0021_auto_20200528_0732': [create_initial_koodisto_data],
            '0023_historicalpidempipoissaolo_pidempipoissaolo': [create_henkilosto_template_groups],
            '0034_auto_20201029_1603': [create_toimijatiedot_template_groups],
            '0036_postinumero_koodit': [create_postinumero_koodisto_data],
            '0037_auto_20201126_1055': [create_virhe_koodisto_data],
            '0038_auto_20201201_1237': [create_raportit_template_groups],
            '0045_auto_20210318_0953': [create_oph_luovutuspalvelu_group],
            '0060_yritysmuoto': [create_yritysmuoto_koodisto_data, load_dev_testing_data]
        }

        for migration_plan_tuple in kwargs['plan']:
            migration_action_list = migration_action_dict.get(migration_plan_tuple[0].name, None)
            if (migration_plan_tuple[0].app_label == 'varda' and
                    not migration_plan_tuple[1] and
                    isinstance(migration_action_list, list)):
                for migration_action in migration_action_list:
                    migration_action()


def load_dev_testing_data():
    # Note: If you are adding new permissions this might need to be moved to current migration block.
    env_type = os.getenv('VARDA_ENVIRONMENT_TYPE', None)
    if env_type is None or env_type not in ['env-varda-prod', 'prod']:
        load_testing_data()


def receiver_save_user(**kwargs):
    from django.utils import timezone
    from varda.cache import delete_object_ids_user_has_permissions
    from varda.models import Z7_AdditionalUserFields

    created = kwargs['created']
    update_fields = kwargs['update_fields']
    user = kwargs['instance']

    if not created and update_fields is None:
        """
        User permissions changed "on-the-fly".
        We need to remove the cache for user - varda.cache.get_object_ids_user_has_permissions
        """
        user_id = user.id
        delete_object_ids_user_has_permissions(user_id)
    elif created and user.is_staff and user.has_usable_password():
        # Update password_changed_timestamp when staff user is created
        now = timezone.now()
        Z7_AdditionalUserFields.objects.update_or_create(user=user, defaults={'password_changed_timestamp': now})


def receiver_pre_save_user(**kwargs):
    from django.utils import timezone
    from varda.models import User, Z7_AdditionalUserFields

    instance = kwargs['instance']
    if not getattr(instance, 'pk', None):
        # User is created, handle in post_save so that we can create related Z7_AdditionalUserFields object
        return

    user = User.objects.get(pk=instance.pk)
    if instance.is_staff and instance.has_usable_password() and instance.password != user.password:
        # Update password_changed_timestamp when staff user password is changed
        now = timezone.now()
        Z7_AdditionalUserFields.objects.update_or_create(user=instance, defaults={'password_changed_timestamp': now})


def receiver_pre_save(sender, **kwargs):
    from django.db import transaction
    from varda.tasks import change_paos_tallentaja_organization_task

    model_name = sender._meta.model.__name__.lower()
    instance = kwargs['instance']

    with transaction.atomic():
        if model_name == 'paosoikeus':
            """
            We need to change permissions (due to PAOS) to other organization if voimassa_kytkin changes.
            """
            instance_id = instance.id
            if instance_id is None:
                """
                This is a new instance. New instance has voimassa_kytkin always False ==> Nothing to do.
                """
                pass
            else:
                """
                Update of an existing PaosOikeus-obj.
                tallentaja_organization changed.
                """
                new_instance_voimassa_kytkin = instance.voimassa_kytkin
                change_paos_tallentaja_organization_task.delay(instance.jarjestaja_kunta_organisaatio.id,
                                                               instance.tuottaja_organisaatio.id,
                                                               instance.tallentaja_organisaatio.id,
                                                               new_instance_voimassa_kytkin)


def tutkinto_tyontekija_id_lookup(instance):
    from varda.models import Tyontekija

    return (Tyontekija.objects.filter(vakajarjestaja=instance.vakajarjestaja, henkilo=instance.henkilo)
            .values_list('id', flat=True).first())


def update_related_object_change(instance, timestamp, history_type, model_name='', path_to_id=('id',),
                                 custom_id_lookup=None, parent_model_name=None, path_to_parent_id=None,
                                 create_parent_record=True):
    """
    A function that updates Z9_RelatedObjectChanged table to reflect any related changes made
    e.g. Varhaiskasvatussuhde is changed -> means that information of certain Lapsi object is changed
    :param instance: object instance that triggered the operation
    :param timestamp: timestamp
    :param history_type: history type string (+, ~ or -)
    :param model_name: name of the target model
    :param path_to_id: iterable of strings that lead to id
    :param custom_id_lookup: function, can be provided for custom id lookup
    :param parent_model_name: name of the parent model (e.g. Varhaiskasvatussuhde is changed, Varhaiskasvatuspaatos is
                              the main model and Lapsi is the parent model
    :param create_parent_record: boolean, determines if record for parent should also be created
    :param path_to_parent_id: iterable of strings that lead to parent id
    """
    from varda.misc import get_nested_value
    from varda.models import Z9_RelatedObjectChanged

    instance_id = custom_id_lookup(instance) if custom_id_lookup else get_nested_value(instance, path_to_id)
    if not instance_id:
        # In some cases instance_id may be null, e.g. custom_id_lookup and some manual operations, in that case
        # we do not want to do anything
        return None

    parent_instance_id = None
    if parent_model_name:
        parent_instance_id = get_nested_value(instance, path_to_parent_id)
    additional_values = {'parent_model_name': parent_model_name,
                         'parent_instance_id': parent_instance_id} if parent_instance_id else {}

    Z9_RelatedObjectChanged.objects.create(model_name=model_name, instance_id=instance_id,
                                           changed_timestamp=timestamp, history_type=history_type,
                                           trigger_model_name=instance.__class__.get_name(),
                                           trigger_instance_id=instance.id,
                                           **additional_values)
    if parent_instance_id and create_parent_record:
        Z9_RelatedObjectChanged.objects.create(model_name=parent_model_name, instance_id=parent_instance_id,
                                               changed_timestamp=timestamp, history_type=history_type,
                                               trigger_model_name=instance.__class__.get_name(),
                                               trigger_instance_id=instance.id)


def update_related_object_change_henkilo(instance, timestamp, history_type):
    """
    Custom related object change handling for Henkilo relations. We want to mask changes made to Henkilo
    to look like the change was made to Lapsi/Tyontekija/Huoltajuussuhde, because if Lapsi/Tyontekija/Huoltajuussuhde
    is added and removed during the time window (no change), we don't want that change in Henkilo during the time
    window is registered as a change
    :param instance: Henkilo object instance that triggered the operation
    :param timestamp: timestamp
    :param history_type: history type string (+, ~ or -)
    """
    from varda.models import Huoltajuussuhde, Lapsi, Tyontekija, Z9_RelatedObjectChanged

    if huoltaja := getattr(instance, 'huoltaja', None):
        for huoltajuussuhde in huoltaja.huoltajuussuhteet.all():
            Z9_RelatedObjectChanged.objects.create(model_name=Lapsi.get_name(),
                                                   instance_id=huoltajuussuhde.lapsi_id,
                                                   changed_timestamp=timestamp, history_type=history_type,
                                                   trigger_model_name=Huoltajuussuhde.get_name(),
                                                   trigger_instance_id=huoltajuussuhde.id)

    for lapsi in instance.lapsi.all():
        Z9_RelatedObjectChanged.objects.create(model_name=Lapsi.get_name(), instance_id=lapsi.id,
                                               changed_timestamp=timestamp, history_type=history_type,
                                               trigger_model_name=Lapsi.get_name(), trigger_instance_id=lapsi.id)

    for tyontekija in instance.tyontekijat.all():
        Z9_RelatedObjectChanged.objects.create(model_name=Tyontekija.get_name(), instance_id=tyontekija.id,
                                               changed_timestamp=timestamp, history_type=history_type,
                                               trigger_model_name=Tyontekija.get_name(),
                                               trigger_instance_id=tyontekija.id)


def update_related_object_change_maksutieto(instance, timestamp, history_type):
    from varda.models import Lapsi, Maksutieto, MaksutietoHuoltajuussuhde, Z9_RelatedObjectChanged

    for maksutieto_huoltajuussuhde in instance.maksutiedot_huoltajuussuhteet.all():
        Z9_RelatedObjectChanged.objects.create(model_name=Lapsi.get_name(),
                                               instance_id=maksutieto_huoltajuussuhde.huoltajuussuhde.lapsi_id,
                                               changed_timestamp=timestamp, history_type=history_type,
                                               trigger_model_name=MaksutietoHuoltajuussuhde.get_name(),
                                               trigger_instance_id=maksutieto_huoltajuussuhde.id,
                                               parent_model_name=Maksutieto.get_name(),
                                               parent_instance_id=maksutieto_huoltajuussuhde.maksutieto_id)


def update_related_object_change_taydennyskoulutus(instance, timestamp, history_type):
    from varda.models import Taydennyskoulutus, TaydennyskoulutusTyontekija, Tyontekija, Z9_RelatedObjectChanged

    for taydennyskoulutus_tyontekija in instance.taydennyskoulutukset_tyontekijat.all():
        Z9_RelatedObjectChanged.objects.create(model_name=Tyontekija.get_name(),
                                               instance_id=taydennyskoulutus_tyontekija.tyontekija_id,
                                               changed_timestamp=timestamp, history_type=history_type,
                                               trigger_model_name=TaydennyskoulutusTyontekija.get_name(),
                                               trigger_instance_id=taydennyskoulutus_tyontekija.id,
                                               parent_model_name=Taydennyskoulutus.get_name(),
                                               parent_instance_id=taydennyskoulutus_tyontekija.taydennyskoulutus_id)


def handle_related_object_change(model_name, instance, history_type):
    from varda.models import (Henkilo, Huoltajuussuhde, KieliPainotus, Lapsi, Maksutieto, MaksutietoHuoltajuussuhde,
                              Palvelussuhde, PidempiPoissaolo, Taydennyskoulutus, TaydennyskoulutusTyontekija,
                              TilapainenHenkilosto, ToiminnallinenPainotus, Toimipaikka, Tutkinto, Tyontekija,
                              Tyoskentelypaikka, VakaJarjestaja, Varhaiskasvatuspaatos, Varhaiskasvatussuhde)

    receiver_dict = {
        VakaJarjestaja.get_name(): partial(update_related_object_change, model_name=VakaJarjestaja.get_name(),
                                           path_to_id=('id',)),
        Toimipaikka.get_name(): partial(update_related_object_change, model_name=Toimipaikka.get_name(),
                                        path_to_id=('id',), parent_model_name=VakaJarjestaja.get_name(),
                                        path_to_parent_id=('vakajarjestaja_id',)),
        ToiminnallinenPainotus.get_name(): partial(update_related_object_change, model_name=Toimipaikka.get_name(),
                                                   path_to_id=('toimipaikka_id',),
                                                   parent_model_name=VakaJarjestaja.get_name(),
                                                   path_to_parent_id=('toimipaikka', 'vakajarjestaja_id',)),
        KieliPainotus.get_name(): partial(update_related_object_change, model_name=Toimipaikka.get_name(),
                                          path_to_id=('toimipaikka_id',), parent_model_name=VakaJarjestaja.get_name(),
                                          path_to_parent_id=('toimipaikka', 'vakajarjestaja_id',)),
        Henkilo.get_name(): partial(update_related_object_change_henkilo),
        Lapsi.get_name(): partial(update_related_object_change, model_name=Lapsi.get_name(), path_to_id=('id',)),
        Varhaiskasvatuspaatos.get_name(): partial(update_related_object_change,
                                                  model_name=Varhaiskasvatuspaatos.get_name(),
                                                  path_to_id=('id',), parent_model_name=Lapsi.get_name(),
                                                  path_to_parent_id=('lapsi_id',)),
        Varhaiskasvatussuhde.get_name(): partial(update_related_object_change,
                                                 model_name=Varhaiskasvatuspaatos.get_name(),
                                                 path_to_id=('varhaiskasvatuspaatos_id',),
                                                 parent_model_name=Lapsi.get_name(),
                                                 path_to_parent_id=('varhaiskasvatuspaatos', 'lapsi_id',)),
        Huoltajuussuhde.get_name(): partial(update_related_object_change, model_name=Lapsi.get_name(),
                                            path_to_id=('lapsi_id',)),
        Maksutieto.get_name(): update_related_object_change_maksutieto,
        MaksutietoHuoltajuussuhde.get_name(): partial(update_related_object_change, model_name=Lapsi.get_name(),
                                                      path_to_id=('huoltajuussuhde', 'lapsi_id',),
                                                      parent_model_name=Maksutieto.get_name(),
                                                      path_to_parent_id=('maksutieto_id',)),
        Tyontekija.get_name(): partial(update_related_object_change, model_name=Tyontekija.get_name(),
                                       path_to_id=('id',)),
        Tutkinto.get_name(): partial(update_related_object_change, model_name=Tyontekija.get_name(),
                                     custom_id_lookup=tutkinto_tyontekija_id_lookup),
        Palvelussuhde.get_name(): partial(update_related_object_change, model_name=Palvelussuhde.get_name(),
                                          path_to_id=('id',), parent_model_name=Tyontekija.get_name(),
                                          path_to_parent_id=('tyontekija_id',)),
        Tyoskentelypaikka.get_name(): partial(update_related_object_change, model_name=Palvelussuhde.get_name(),
                                              path_to_id=('palvelussuhde_id',), parent_model_name=Tyontekija.get_name(),
                                              path_to_parent_id=('palvelussuhde', 'tyontekija_id',)),
        PidempiPoissaolo.get_name(): partial(update_related_object_change, model_name=Palvelussuhde.get_name(),
                                             path_to_id=('palvelussuhde_id',), parent_model_name=Tyontekija.get_name(),
                                             path_to_parent_id=('palvelussuhde', 'tyontekija_id',)),
        Taydennyskoulutus.get_name(): update_related_object_change_taydennyskoulutus,
        TaydennyskoulutusTyontekija.get_name(): partial(update_related_object_change, model_name=Tyontekija.get_name(),
                                                        path_to_id=('tyontekija_id',),
                                                        parent_model_name=Taydennyskoulutus.get_name(),
                                                        path_to_parent_id=('taydennyskoulutus_id',)),
        TilapainenHenkilosto.get_name(): partial(update_related_object_change, model_name=VakaJarjestaja.get_name(),
                                                 path_to_id=('vakajarjestaja_id',))
    }

    if model_name in receiver_dict:
        timestamp = timezone.now()
        receiver_dict[model_name](instance, timestamp, history_type)


def receiver_save(sender, **kwargs):
    from django.db import transaction
    from varda.cache import invalidate_cache
    from varda.models import Lapsi

    model_name = sender._meta.model.__name__.lower()
    instance = kwargs['instance']
    instance_id = instance.id
    invalidate_cache(model_name, instance_id)

    if model_name == Lapsi.get_name():
        with transaction.atomic():
            post_save.disconnect(receiver_save, sender='varda.Lapsi')
            if instance.paos_organisaatio is None:
                instance.paos_kytkin = False
            else:
                instance.paos_kytkin = True
            instance.save()
            post_save.connect(receiver_save, sender='varda.Lapsi')

    handle_related_object_change(model_name, instance, '+' if kwargs['created'] else '~')


def receiver_pre_delete(sender, **kwargs):
    from varda.cache import invalidate_cache
    from varda.permissions import delete_object_permissions_explicitly
    from varda.tasks import change_paos_tallentaja_organization_task

    model = sender._meta.model
    model_name = model.__name__.lower()
    instance = kwargs['instance']
    instance_id = instance.id

    invalidate_cache(model_name, instance_id)
    delete_object_permissions_explicitly(model, instance_id)

    if model_name == 'paosoikeus' and instance.voimassa_kytkin:
        """
        Deleting the instance is the same as setting the voimassa_kytkin to False (in permission point of view).
        """
        deleted_instance_voimassa_kytkin = False
        change_paos_tallentaja_organization_task.delay(instance.jarjestaja_kunta_organisaatio.id,
                                                       instance.tuottaja_organisaatio.id,
                                                       instance.tallentaja_organisaatio.id,
                                                       deleted_instance_voimassa_kytkin)

    handle_related_object_change(model_name, instance, '-')


def init_alive_log():
    if settings.PRODUCTION_ENV or settings.QA_ENV:
        log_seq = 0
        boot_time = timezone.now()
        cache.set(ALIVE_SEQ_CACHE_KEY, log_seq, None)
        cache.set(ALIVE_BOOT_TIME_CACHE_KEY, boot_time, None)
        return log_seq, boot_time
    return None


class VardaConfig(AppConfig):
    name = 'varda'

    def ready(self):
        post_migrate.connect(run_post_migration_tasks, sender=self)

        pre_save.connect(receiver_pre_save, sender='varda.VakaJarjestaja')
        pre_save.connect(receiver_pre_save, sender='varda.PaosOikeus')
        pre_save.connect(receiver_pre_save_user, sender='auth.User')

        post_save.connect(receiver_save_user, sender='auth.User')
        post_save.connect(receiver_save, sender='varda.VakaJarjestaja')
        post_save.connect(receiver_save, sender='varda.Toimipaikka')
        post_save.connect(receiver_save, sender='varda.ToiminnallinenPainotus')
        post_save.connect(receiver_save, sender='varda.KieliPainotus')
        post_save.connect(receiver_save, sender='varda.Henkilo')
        post_save.connect(receiver_save, sender='varda.Lapsi')
        post_save.connect(receiver_save, sender='varda.Varhaiskasvatuspaatos')
        post_save.connect(receiver_save, sender='varda.Varhaiskasvatussuhde')
        post_save.connect(receiver_save, sender='varda.Huoltajuussuhde')
        post_save.connect(receiver_save, sender='varda.Maksutieto')
        post_save.connect(receiver_save, sender='varda.MaksutietoHuoltajuussuhde')
        post_save.connect(receiver_save, sender='varda.PaosToiminta')
        post_save.connect(receiver_save, sender='varda.PaosOikeus')
        post_save.connect(receiver_save, sender='varda.Tyontekija')
        post_save.connect(receiver_save, sender='varda.TilapainenHenkilosto')
        post_save.connect(receiver_save, sender='varda.Tutkinto')
        post_save.connect(receiver_save, sender='varda.Palvelussuhde')
        post_save.connect(receiver_save, sender='varda.Tyoskentelypaikka')
        post_save.connect(receiver_save, sender='varda.PidempiPoissaolo')
        post_save.connect(receiver_save, sender='varda.Taydennyskoulutus')
        post_save.connect(receiver_save, sender='varda.TaydennyskoulutusTyontekija')

        pre_delete.connect(receiver_pre_delete, sender='varda.VakaJarjestaja')
        pre_delete.connect(receiver_pre_delete, sender='varda.Toimipaikka')
        pre_delete.connect(receiver_pre_delete, sender='varda.ToiminnallinenPainotus')
        pre_delete.connect(receiver_pre_delete, sender='varda.KieliPainotus')
        pre_delete.connect(receiver_pre_delete, sender='varda.Henkilo')
        pre_delete.connect(receiver_pre_delete, sender='varda.Lapsi')
        pre_delete.connect(receiver_pre_delete, sender='varda.Varhaiskasvatuspaatos')
        pre_delete.connect(receiver_pre_delete, sender='varda.Varhaiskasvatussuhde')
        pre_delete.connect(receiver_pre_delete, sender='varda.Huoltajuussuhde')
        pre_delete.connect(receiver_pre_delete, sender='varda.Maksutieto')
        pre_delete.connect(receiver_pre_delete, sender='varda.MaksutietoHuoltajuussuhde')
        pre_delete.connect(receiver_pre_delete, sender='varda.PaosToiminta')
        pre_delete.connect(receiver_pre_delete, sender='varda.PaosOikeus')
        pre_delete.connect(receiver_pre_delete, sender='varda.Tyontekija')
        pre_delete.connect(receiver_pre_delete, sender='varda.TilapainenHenkilosto')
        pre_delete.connect(receiver_pre_delete, sender='varda.Tutkinto')
        pre_delete.connect(receiver_pre_delete, sender='varda.Palvelussuhde')
        pre_delete.connect(receiver_pre_delete, sender='varda.Tyoskentelypaikka')
        pre_delete.connect(receiver_pre_delete, sender='varda.PidempiPoissaolo')
        pre_delete.connect(receiver_pre_delete, sender='varda.Taydennyskoulutus')
        pre_delete.connect(receiver_pre_delete, sender='varda.TaydennyskoulutusTyontekija')

        init_alive_log()
