import datetime
import logging

from django.conf import settings
from django.db import migrations, models, connection
import django.db.models.deletion
import simple_history.models

logger = logging.getLogger(__name__)


def forwards_func(apps, schema_editor):
    """
    Create corresponding MaksutietoHuoltajuussuhde records of existing Maksutieto Huoltajuussuhde relation.
    """
    with connection.cursor() as cursor:
        logger.info(f'Starting MaksutietoHuoltajuussuhde creation at {datetime.datetime.now()}')
        cursor.execute('INSERT INTO varda_maksutietohuoltajuussuhde (huoltajuussuhde_id, maksutieto_id, changed_by_id, luonti_pvm, muutos_pvm) '
                       'SELECT hsmt.huoltajuussuhde_id, hsmt.maksutieto_id, mt.changed_by_id, mt.luonti_pvm, mt.luonti_pvm '
                       'FROM varda_huoltajuussuhde_maksutiedot hsmt '
                       'LEFT JOIN varda_maksutieto mt on hsmt.maksutieto_id = mt.id;')
        logger.info(f'Ending MaksutietoHuoltajuussuhde creation at {datetime.datetime.now()}')
        logger.info(f'Starting MaksutietoHuoltajuussuhde history creation at {datetime.datetime.now()}')
        cursor.execute('INSERT INTO varda_historicalmaksutietohuoltajuussuhde (id, luonti_pvm, muutos_pvm, history_date, history_type, changed_by_id, history_user_id, huoltajuussuhde_id, maksutieto_id) '
                       'SELECT id, luonti_pvm, muutos_pvm, muutos_pvm, \'+\', changed_by_id, changed_by_id, huoltajuussuhde_id, maksutieto_id '
                       'FROM varda_maksutietohuoltajuussuhde;')
        logger.info(f'Ending MaksutietoHuoltajuussuhde history creation at {datetime.datetime.now()}')


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0053_auto_20210914_1536'),
    ]

    operations = [
        migrations.CreateModel(
            name='MaksutietoHuoltajuussuhde',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('luonti_pvm', models.DateTimeField(auto_now_add=True)),
                ('muutos_pvm', models.DateTimeField(auto_now=True)),
                ('changed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='maksutiedot_huoltajuussuhteet', to=settings.AUTH_USER_MODEL)),
                ('huoltajuussuhde', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='maksutiedot_huoltajuussuhteet', to='varda.huoltajuussuhde')),
                ('maksutieto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='maksutiedot_huoltajuussuhteet', to='varda.maksutieto')),
            ],
            options={
                'verbose_name_plural': 'maksutiedot huoltajuussuhteet',
            },
        ),
        migrations.CreateModel(
            name='HistoricalMaksutietoHuoltajuussuhde',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('luonti_pvm', models.DateTimeField(blank=True, editable=False)),
                ('muutos_pvm', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('changed_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('huoltajuussuhde', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.huoltajuussuhde')),
                ('maksutieto', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.maksutieto')),
            ],
            options={
                'verbose_name': 'historical maksutieto huoltajuussuhde',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.RunPython(forwards_func, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='huoltajuussuhde',
            name='maksutiedot',
        ),
        migrations.AddField(
            model_name='huoltajuussuhde',
            name='maksutiedot',
            field=models.ManyToManyField(blank=True, related_name='huoltajuussuhteet', through='varda.MaksutietoHuoltajuussuhde', to='varda.Maksutieto'),
        ),
    ]
