# Generated by Django 3.1.4 on 2021-05-26 13:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0048_auto_20210520_1227'),
    ]

    operations = [
        migrations.CreateModel(
            name='Z6_LastRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lahdejarjestelma', models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi])),
                ('last_successful', models.DateTimeField(null=True)),
                ('last_unsuccessful', models.DateTimeField(null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='last_requests', to=settings.AUTH_USER_MODEL)),
                ('vakajarjestaja', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='last_requests', to='varda.vakajarjestaja')),
            ],
            options={
                'verbose_name_plural': 'Last requests',
            },
        ),
        migrations.AddConstraint(
            model_name='z6_lastrequest',
            constraint=models.UniqueConstraint(fields=('user', 'vakajarjestaja', 'lahdejarjestelma'), name='last_request_user_vakajarjestaja_lahdejarjestelma_unique_constraint'),
        ),
    ]