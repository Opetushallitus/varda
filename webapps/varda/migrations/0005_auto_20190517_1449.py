# Generated by Django 2.1.7 on 2019-05-17 11:49
import os

from django.db import migrations


os_name = os.getenv('VARDA_MIGRATION_OS_OVERRIDE', os.name)


def get_locale_name():
    # Windows uses utf8 with any locale in postgres
    if os_name == 'nt':
        return 'fi-FI'
    return 'fi_FI.utf8'


def get_old_collation_name():
    # Windows uses utf8 with any locale in postgres
    if os_name == 'nt':
        return 'default'
    return 'en_US.utf8'


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0004_auto_20190515_0434'),
    ]

    # Postgres specific operations
    operations = [
        migrations.RunSQL('CREATE COLLATION fi_fi (locale = "{}");'.format(get_locale_name()),
                          'DROP COLLATION fi_fi;'),
        migrations.RunSQL('ALTER TABLE varda_henkilo ALTER COLUMN etunimet TYPE VARCHAR (100) COLLATE fi_fi;',
                          'ALTER TABLE varda_henkilo ALTER COLUMN etunimet TYPE VARCHAR (100) COLLATE "{}";'.format(get_old_collation_name())),
        migrations.RunSQL('ALTER TABLE varda_henkilo ALTER COLUMN kutsumanimi TYPE VARCHAR (100) COLLATE fi_fi;',
                          'ALTER TABLE varda_henkilo ALTER COLUMN kutsumanimi TYPE VARCHAR (100) COLLATE "{}";'.format(get_old_collation_name())),
        migrations.RunSQL('ALTER TABLE varda_henkilo ALTER COLUMN sukunimi TYPE VARCHAR (100) COLLATE fi_fi;',
                          'ALTER TABLE varda_henkilo ALTER COLUMN sukunimi TYPE VARCHAR (100) COLLATE "{}";'.format(get_old_collation_name())),
        migrations.RunSQL('ALTER TABLE varda_toimipaikka ALTER COLUMN nimi TYPE VARCHAR (100) COLLATE fi_fi;',
                          'ALTER TABLE varda_toimipaikka ALTER COLUMN nimi TYPE VARCHAR (100) COLLATE "{}";'.format(get_old_collation_name())),
        migrations.RunSQL('ALTER TABLE varda_toimipaikka ALTER COLUMN nimi_sv TYPE VARCHAR (100) COLLATE fi_fi;',
                          'ALTER TABLE varda_toimipaikka ALTER COLUMN nimi_sv TYPE VARCHAR (100) COLLATE "{}";'.format(get_old_collation_name()))
    ]
