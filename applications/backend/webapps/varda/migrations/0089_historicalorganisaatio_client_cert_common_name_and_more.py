# Generated by Django 4.2.9 on 2024-03-25 12:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0088_lapsi_lapsi_vakatoimija_unique_constraint'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalorganisaatio',
            name='client_cert_common_name',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='organisaatio',
            name='client_cert_common_name',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.CreateModel(
            name='LuovutuspalveluClientCsr',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_cert_s3_bucket_key', models.CharField(blank=True, max_length=200, null=True)),
                ('cert_chain_s3_bucket_key', models.CharField(blank=True, max_length=200, null=True)),
                ('expiration_date', models.DateTimeField(null=True)),
                ('luonti_pvm', models.DateTimeField(auto_now_add=True)),
                ('organisaatio', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='client_csrs', to='varda.organisaatio')),
            ],
            options={
                'verbose_name_plural': 'Client CSRs',
            },
        ),
        migrations.CreateModel(
            name='HistoricalLuovutuspalveluClientCsr',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('client_cert_s3_bucket_key', models.CharField(blank=True, max_length=200, null=True)),
                ('cert_chain_s3_bucket_key', models.CharField(blank=True, max_length=200, null=True)),
                ('expiration_date', models.DateTimeField(null=True)),
                ('luonti_pvm', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisaatio', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.organisaatio')),
            ],
            options={
                'verbose_name': 'historical luovutuspalvelu client csr',
                'verbose_name_plural': 'historical Client CSRs',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
