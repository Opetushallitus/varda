# Generated by Django 3.1.4 on 2021-08-26 06:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0049_auto_20210526_1613'),
    ]

    operations = [
        migrations.AddField(
            model_name='z8_excelreportlog',
            name='encryption_duration',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='aikaleima',
            name='avain',
            field=models.TextField(choices=[('AUDIT_LOG_AWS_LAST_UPDATE', 'AUDIT_LOG_AWS_LAST_UPDATE'), ('HENKILOMUUTOS_LAST_UPDATE', 'HENKILOMUUTOS_LAST_UPDATE'), ('HUOLTAJASUHDEMUUTOS_LAST_UPDATE', 'HUOLTAJASUHDEMUUTOS_LAST_UPDATE'), ('ORGANISAATIOS_LAST_UPDATE', 'ORGANISAATIOS_LAST_UPDATE'), ('ORGANISAATIOS_VARDA_LAST_UPDATE', 'ORGANISAATIOS_VARDA_LAST_UPDATE'), ('REQUEST_SUMMARY_LAST_UPDATE', 'REQUEST_SUMMARY_LAST_UPDATE')], unique=True),
        ),
        migrations.CreateModel(
            name='Z6_RequestSummary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lahdejarjestelma', models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi])),
                ('request_url_simple', models.CharField(max_length=200, null=True)),
                ('summary_date', models.DateField()),
                ('successful_count', models.IntegerField()),
                ('unsuccessful_count', models.IntegerField()),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='request_summaries', to=settings.AUTH_USER_MODEL)),
                ('vakajarjestaja', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='request_summaries', to='varda.vakajarjestaja')),
            ],
            options={
                'verbose_name_plural': 'Request summaries',
            },
        ),
        migrations.CreateModel(
            name='Z6_RequestCount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_url_simple', models.CharField(max_length=200)),
                ('request_method', models.CharField(max_length=10)),
                ('response_code', models.IntegerField()),
                ('count', models.IntegerField()),
                ('request_summary', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='request_counts', to='varda.z6_requestsummary')),
            ],
            options={
                'verbose_name_plural': 'Request counts',
            },
        ),
        migrations.AddConstraint(
            model_name='z6_requestsummary',
            constraint=models.UniqueConstraint(condition=models.Q(user__isnull=False), fields=('user', 'summary_date'), name='request_summary_user_summary_date_unique_constraint'),
        ),
        migrations.AddConstraint(
            model_name='z6_requestsummary',
            constraint=models.UniqueConstraint(condition=models.Q(vakajarjestaja__isnull=False), fields=('vakajarjestaja', 'summary_date'), name='request_summary_vakajarjestaja_summary_date_unique_constraint'),
        ),
        migrations.AddConstraint(
            model_name='z6_requestsummary',
            constraint=models.UniqueConstraint(condition=models.Q(lahdejarjestelma__isnull=False), fields=('lahdejarjestelma', 'summary_date'), name='request_summary_lahdejarjestelma_summary_date_unique_constraint'),
        ),
        migrations.AddConstraint(
            model_name='z6_requestsummary',
            constraint=models.UniqueConstraint(condition=models.Q(request_url_simple__isnull=False), fields=('request_url_simple', 'summary_date'), name='request_summary_request_url_simple_summary_date_unique_constraint'),
        ),
        migrations.AddConstraint(
            model_name='z6_requestcount',
            constraint=models.UniqueConstraint(fields=('request_summary', 'request_url_simple', 'request_method', 'response_code'), name='request_count_unique_constraint'),
        ),
    ]