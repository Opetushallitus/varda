# Generated by Django 4.2 on 2023-06-16 08:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0083_historicalkielipainotus_kielipainotustyyppi_koodi_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='z6_lastrequest',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='last_requests', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='z6_requestlog',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='request_log', to=settings.AUTH_USER_MODEL),
        ),
    ]
