# Generated by Django 2.2.11 on 2020-05-26 07:14

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0022_historicalpalvelussuhde_palvelussuhde'),
    ]

    operations = [
        migrations.CreateModel(
            name='Z2_Code',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_value', models.CharField(max_length=256)),
            ],
            options={
                'verbose_name_plural': 'Varda codes',
            },
        ),
        migrations.AlterModelOptions(
            name='z2_koodisto',
            options={'verbose_name_plural': 'Varda koodistot'},
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='jarjestamismuoto_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='kasvatusopillinen_jarjestelma_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='kieli_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='kunta_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='lahdejarjestelma_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='maksun_peruste_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='opiskeluoikeuden_tila_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='sukupuoli_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='toiminnallinen_painotus_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='toimintamuoto_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='tutkinto_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='tutkintonimike_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='tyoaika_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='tyosuhde_koodit',
        ),
        migrations.RemoveField(
            model_name='z2_koodisto',
            name='tyotehtava_koodit',
        ),
        migrations.AddField(
            model_name='z2_koodisto',
            name='update_datetime',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='z2_koodisto',
            name='name',
            field=models.CharField(default='', max_length=256, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='z2_koodisto',
            name='name_koodistopalvelu',
            field=models.CharField(default='', max_length=256, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='z2_koodisto',
            name='version',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='Z2_CodeTranslation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(max_length=10)),
                ('name', models.CharField(blank=True, max_length=256)),
                ('description', models.CharField(blank=True, max_length=2048)),
                ('short_name', models.CharField(blank=True, max_length=256)),
                ('code', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='translations', to='varda.Z2_Code')),
            ],
            options={
                'verbose_name_plural': 'Varda code translations',
            },
        ),
        migrations.AddField(
            model_name='z2_code',
            name='koodisto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='codes', to='varda.Z2_Koodisto'),
        ),
        migrations.AddConstraint(
            model_name='z2_codetranslation',
            constraint=models.UniqueConstraint(fields=('code', 'language'), name='code_language_unique_constraint'),
        ),
        migrations.AddConstraint(
            model_name='z2_code',
            constraint=models.UniqueConstraint(fields=('koodisto', 'code_value'), name='koodisto_code_value_unique_constraint'),
        ),
    ]
