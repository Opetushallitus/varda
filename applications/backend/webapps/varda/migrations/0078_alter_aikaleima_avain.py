# Generated by Django 4.1.7 on 2023-03-17 14:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0077_vuokrattuhenkilosto_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aikaleima',
            name='avain',
            field=models.CharField(max_length=200, unique=True),
        ),
    ]
