# Generated by Django 3.2.11 on 2022-01-27 14:23

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


def forwards_func(apps, schema_editor):
    # RenameModel creates new Permission objects for Organisaatio-model
    # We want to rename old VakaJarjestaja Permission objects to match new model name so that we don't need to
    # rebuild all group permissions
    Permission = apps.get_model('auth', 'Permission')
    db_alias = schema_editor.connection.alias
    Permission.objects.using(db_alias).filter(Q(codename__endswith='_organisaatio') |
                                              Q(codename__endswith='_historicalorganisaatio')).delete()
    rename_permissions(Permission, db_alias, 'vakajarjestaja', 'organisaatio')


def reverse_func(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    db_alias = schema_editor.connection.alias
    rename_permissions(Permission, db_alias, 'organisaatio', 'vakajarjestaja')


def rename_permissions(Permission, db_alias, old_model_name, new_model_name):
    for permission in Permission.objects.using(db_alias).filter(Q(codename__endswith=f'_{old_model_name}') |
                                                                Q(codename__endswith=f'_historical{old_model_name}')):
        historical = 'historical ' if 'historical' in permission.name else ''
        permission_type = permission.codename.split('_')[0]
        permission.codename = f'{permission_type}_{historical.strip()}{new_model_name}'
        permission_name_list = permission.name.split(' ')
        permission.name = f'{permission_name_list[0]} {permission_name_list[1]} {historical}{new_model_name}'
        permission.save()


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0065_remove_z3_additionalcasuserfields_approved_oph_staff_and_more'),
    ]

    operations = [
        migrations.RenameModel('VakaJarjestaja', 'Organisaatio'),
        migrations.RenameModel('HistoricalVakaJarjestaja', 'HistoricalOrganisaatio'),
        migrations.AlterModelOptions(
            name='historicalorganisaatio',
            options={'get_latest_by': 'history_date', 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical organisaatio'},
        ),
        migrations.AlterModelOptions(
            name='organisaatio',
            options={'verbose_name_plural': 'organisaatiot'},
        ),
        migrations.AddField(
            model_name='historicalorganisaatio',
            name='organisaatiotyyppi',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), default=list, size=None),
        ),
        migrations.AddField(
            model_name='organisaatio',
            name='organisaatiotyyppi',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), default=list, size=None),
        ),
        # Set default value as '' so that this migration is reversible
        migrations.AlterField(
            model_name='logincertificate',
            name='organisation_name',
            field=models.CharField(max_length=50, blank=True, default='')
        ),
        migrations.RemoveField(
            model_name='logincertificate',
            name='organisation_name',
        ),
        migrations.AddField(
            model_name='logincertificate',
            name='organisaatio',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='logincertificates', to='varda.organisaatio'),
        ),
        migrations.AlterField(
            model_name='logincertificate',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='logincertificates', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(forwards_func, reverse_code=reverse_func)
    ]
