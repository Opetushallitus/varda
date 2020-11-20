import os

from django.apps import AppConfig
from django.db.models.signals import post_migrate, post_save, pre_save, pre_delete

from varda.migrations.production.setup import (load_initial_data, create_huoltajatiedot_template_groups,
                                               create_paos_template_groups,
                                               create_henkilosto_template_groups, clear_old_permissions,
                                               modify_change_vakajarjestaja_permission,
                                               create_toimijatiedot_template_groups)
from varda.migrations.testing.setup import (load_testing_data, create_initial_koodisto_data,
                                            create_postinumero_koodisto_data)


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
            '0034_auto_20201029_1603': [create_toimijatiedot_template_groups,
                                        modify_change_vakajarjestaja_permission,
                                        load_dev_testing_data],
            '0036_postinumero_koodit': [create_postinumero_koodisto_data]
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
    if env_type is None or env_type != 'env-varda-prod':
        load_testing_data()


def receiver_auth_user(**kwargs):
    from varda.cache import delete_object_ids_user_has_permissions
    created = kwargs['created']
    update_fields = kwargs['update_fields']
    if not created and update_fields is None:
        """
        User permissions changed "on-the-fly".
        We need to remove the cache for user - varda.cache.get_object_ids_user_has_permissions
        """
        user_id = kwargs['instance'].id
        delete_object_ids_user_has_permissions(user_id)


def receiver_pre_save(sender, **kwargs):
    from django.db import transaction
    from varda.enums.ytj import YtjYritysmuoto
    from varda.tasks import change_paos_tallentaja_organization_task
    model_name = sender._meta.model.__name__.lower()
    instance = kwargs['instance']
    if model_name == 'vakajarjestaja':
        if not YtjYritysmuoto.has_value(instance.yritysmuoto):
            from django.core.exceptions import ValidationError
            raise ValidationError('Yritysmuoto {} is not one of the permitted values.'.format(instance.yritysmuoto))

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


def receiver_save(sender, **kwargs):
    from django.db import transaction
    from varda.cache import invalidate_cache
    model_name = sender._meta.model.__name__.lower()
    instance = kwargs['instance']
    instance_id = instance.id
    invalidate_cache(model_name, instance_id)

    if model_name == 'lapsi':
        with transaction.atomic():
            post_save.disconnect(receiver_save, sender='varda.Lapsi')
            if instance.paos_organisaatio is None:
                instance.paos_kytkin = False
            else:
                instance.paos_kytkin = True
            instance.save()
            post_save.connect(receiver_save, sender='varda.Lapsi')


def receiver_pre_delete(sender, **kwargs):
    from django.contrib.contenttypes.models import ContentType
    from varda.cache import invalidate_cache
    from varda.tasks import change_paos_tallentaja_organization_task, delete_object_permissions_explicitly_task
    model_name = sender._meta.model.__name__.lower()
    instance = kwargs['instance']
    instance_id = instance.id

    invalidate_cache(model_name, instance_id)
    delete_object_permissions_explicitly_task.delay(ContentType.objects.get_for_model(instance).id, instance_id)

    if model_name == 'paosoikeus' and instance.voimassa_kytkin:
        """
        Deleting the instance is the same as setting the voimassa_kytkin to False (in permission point of view).
        """
        deleted_instance_voimassa_kytkin = False
        change_paos_tallentaja_organization_task.delay(instance.jarjestaja_kunta_organisaatio.id,
                                                       instance.tuottaja_organisaatio.id,
                                                       instance.tallentaja_organisaatio.id,
                                                       deleted_instance_voimassa_kytkin)


class VardaConfig(AppConfig):
    name = 'varda'

    def ready(self):
        post_migrate.connect(run_post_migration_tasks, sender=self)

        pre_save.connect(receiver_pre_save, sender='varda.VakaJarjestaja')
        pre_save.connect(receiver_pre_save, sender='varda.PaosOikeus')

        post_save.connect(receiver_auth_user, sender='auth.User')
        post_save.connect(receiver_save, sender='varda.VakaJarjestaja')
        post_save.connect(receiver_save, sender='varda.Toimipaikka')
        post_save.connect(receiver_save, sender='varda.ToiminnallinenPainotus')
        post_save.connect(receiver_save, sender='varda.KieliPainotus')
        post_save.connect(receiver_save, sender='varda.Henkilo')
        post_save.connect(receiver_save, sender='varda.Lapsi')
        post_save.connect(receiver_save, sender='varda.Varhaiskasvatuspaatos')
        post_save.connect(receiver_save, sender='varda.Varhaiskasvatussuhde')
        post_save.connect(receiver_save, sender='varda.Maksutieto')
        post_save.connect(receiver_save, sender='varda.PaosToiminta')
        post_save.connect(receiver_save, sender='varda.PaosOikeus')
        post_save.connect(receiver_save, sender='varda.Tyontekija')
        post_save.connect(receiver_save, sender='varda.TilapainenHenkilosto')
        post_save.connect(receiver_save, sender='varda.Tutkinto')
        post_save.connect(receiver_save, sender='varda.Palvelussuhde')
        post_save.connect(receiver_save, sender='varda.Tyoskentelypaikka')
        post_save.connect(receiver_save, sender='varda.PidempiPoissaolo')
        post_save.connect(receiver_save, sender='varda.Taydennyskoulutus')

        pre_delete.connect(receiver_pre_delete, sender='varda.VakaJarjestaja')
        pre_delete.connect(receiver_pre_delete, sender='varda.Toimipaikka')
        pre_delete.connect(receiver_pre_delete, sender='varda.ToiminnallinenPainotus')
        pre_delete.connect(receiver_pre_delete, sender='varda.KieliPainotus')
        pre_delete.connect(receiver_pre_delete, sender='varda.Henkilo')
        pre_delete.connect(receiver_pre_delete, sender='varda.Lapsi')
        pre_delete.connect(receiver_pre_delete, sender='varda.Varhaiskasvatuspaatos')
        pre_delete.connect(receiver_pre_delete, sender='varda.Varhaiskasvatussuhde')
        pre_delete.connect(receiver_pre_delete, sender='varda.Maksutieto')
        pre_delete.connect(receiver_pre_delete, sender='varda.PaosToiminta')
        pre_delete.connect(receiver_pre_delete, sender='varda.PaosOikeus')
        pre_delete.connect(receiver_pre_delete, sender='varda.Tyontekija')
        pre_delete.connect(receiver_pre_delete, sender='varda.TilapainenHenkilosto')
        pre_delete.connect(receiver_pre_delete, sender='varda.Tutkinto')
        pre_delete.connect(receiver_pre_delete, sender='varda.Palvelussuhde')
        pre_delete.connect(receiver_pre_delete, sender='varda.Tyoskentelypaikka')
        pre_delete.connect(receiver_pre_delete, sender='varda.PidempiPoissaolo')
        pre_delete.connect(receiver_pre_delete, sender='varda.Taydennyskoulutus')
