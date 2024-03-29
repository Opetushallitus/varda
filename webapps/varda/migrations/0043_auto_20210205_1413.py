# Generated by Django 3.1.4 on 2021-02-05 12:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('varda', '0042_auto_20210205_1249'),
    ]

    operations = [
        migrations.CreateModel(
            name='Z7_AdditionalUserFields',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, related_name='additional_user_fields', serialize=False, to='auth.user')),
                ('password_changed_timestamp', models.DateTimeField()),
            ],
            options={
                'verbose_name_plural': 'Additional user fields',
            },
        ),
        migrations.AlterModelOptions(
            name='z3_additionalcasuserfields',
            options={'verbose_name_plural': 'Additional CAS-user fields'},
        ),
        migrations.AlterField(
            model_name='z3_additionalcasuserfields',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, related_name='additional_cas_user_fields', serialize=False, to=settings.AUTH_USER_MODEL),
        ),
    ]
