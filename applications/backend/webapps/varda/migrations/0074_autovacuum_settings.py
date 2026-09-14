from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('varda', '0073_rename_vakajarjestaja_z8_excelreport_organisaatio_and_more'),
    ]

    """
    Override autovacuum settings for guardian_groupobjectpermission, varda_z9_relatedobjectchanged tables and
    varda_z10_kelavarhaiskasvatussuhde.
    https://www.postgresql.org/docs/14/runtime-config-autovacuum.html
    https://www.postgresql.org/docs/current/routine-vacuuming.html#AUTOVACUUM
    autovacuum_vacuum_scale_factor = 0.01 -> run autovacuum when 1% of table is updated or deleted
    autovacuum_vacuum_insert_scale_factor = 0.01 -> run autovacuum when 1% rows of table size is inserted
    autovacuum_analyze_scale_factor = 0.01 -> run autoanalyze when 1% of table is inserted, updated or deleted
    autovacuum_vacuum_cost_limit = 1000 -> increase autovacuum performance (could be done globally)
    """
    operations = [
        migrations.RunSQL(
            ['''ALTER TABLE guardian_groupobjectpermission SET (autovacuum_vacuum_scale_factor = 0.01,
                autovacuum_vacuum_insert_scale_factor = 0.01, autovacuum_analyze_scale_factor = 0.01,
                autovacuum_vacuum_cost_limit = 1000);''',
             '''ALTER TABLE varda_z9_relatedobjectchanged SET (autovacuum_vacuum_scale_factor = 0.01,
                autovacuum_vacuum_insert_scale_factor = 0.01, autovacuum_analyze_scale_factor = 0.01,
                autovacuum_vacuum_cost_limit = 1000);''',
             '''ALTER TABLE varda_z10_kelavarhaiskasvatussuhde SET (autovacuum_vacuum_scale_factor = 0.01,
                autovacuum_vacuum_insert_scale_factor = 0.01, autovacuum_analyze_scale_factor = 0.01,
                autovacuum_vacuum_cost_limit = 1000);'''],
            reverse_sql=['''ALTER TABLE guardian_groupobjectpermission RESET (autovacuum_vacuum_scale_factor,
                            autovacuum_vacuum_insert_scale_factor, autovacuum_analyze_scale_factor,
                            autovacuum_vacuum_cost_limit);''',
                         '''ALTER TABLE varda_z9_relatedobjectchanged RESET (autovacuum_vacuum_scale_factor,
                            autovacuum_vacuum_insert_scale_factor, autovacuum_analyze_scale_factor,
                            autovacuum_vacuum_cost_limit);''',
                         '''ALTER TABLE varda_z10_kelavarhaiskasvatussuhde RESET (autovacuum_vacuum_scale_factor,
                            autovacuum_vacuum_insert_scale_factor, autovacuum_analyze_scale_factor,
                            autovacuum_vacuum_cost_limit);''']
        ),
    ]
