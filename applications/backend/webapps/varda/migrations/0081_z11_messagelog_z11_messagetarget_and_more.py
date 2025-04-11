# Generated by Django 4.1.7 on 2023-03-15 14:36

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0080_remove_z2_codetranslation_short_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Z11_MessageLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message_type', models.CharField(max_length=200)),
                ('email', models.CharField(max_length=200)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'verbose_name_plural': 'message logs',
            },
        ),
        migrations.CreateModel(
            name='Z11_MessageTarget',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_type', models.CharField(max_length=200)),
                ('email', models.CharField(max_length=200)),
                ('language', models.CharField(default='FI', max_length=50)),
            ],
            options={
                'verbose_name_plural': 'message targets',
            },
        ),
        migrations.RemoveConstraint(
            model_name='z6_lastrequest',
            name='last_request_user_vakajarjestaja_lahdejarjestelma_unique_constraint',
        ),
        migrations.AddField(
            model_name='aikaleima',
            name='organisaatio',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='aikaleimat', to='varda.organisaatio'),
        ),
        migrations.AddField(
            model_name='z6_lastrequest',
            name='data_category',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='z6_requestlog',
            name='data_category',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='aikaleima',
            name='avain',
            field=models.CharField(max_length=200),
        ),
        migrations.AddConstraint(
            model_name='aikaleima',
            constraint=models.UniqueConstraint(fields=('avain', 'organisaatio'), name='avain_organisaatio_unique_constraint'),
        ),
        migrations.AddConstraint(
            model_name='aikaleima',
            constraint=models.UniqueConstraint(condition=models.Q(('organisaatio__isnull', True)), fields=('avain',), name='avain_organisaatio_is_null_unique_constraint'),
        ),
        migrations.AddConstraint(
            model_name='z6_lastrequest',
            constraint=models.UniqueConstraint(fields=('user', 'vakajarjestaja', 'lahdejarjestelma', 'data_category'), name='last_request_user_vakaj_lahdej_data_categ_unique_constraint'),
        ),
        migrations.AddField(
            model_name='z11_messagetarget',
            name='organisaatio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='message_targets', to='varda.organisaatio'),
        ),
        migrations.AddField(
            model_name='z11_messagelog',
            name='organisaatio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='message_logs', to='varda.organisaatio'),
        ),
        migrations.AddConstraint(
            model_name='z11_messagetarget',
            constraint=models.UniqueConstraint(fields=('organisaatio', 'user_type', 'email'), name='organisaatio_user_type_email_unique_constraint'),
        ),
    ]
