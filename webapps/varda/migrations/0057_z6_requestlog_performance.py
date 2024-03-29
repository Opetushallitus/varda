# Generated by Django 3.2.7 on 2021-11-25 08:59
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('varda', '0056_auto_20211021_1309'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='z6_requestlog',
            name='varda_z6_re_timesta_96cf31_idx',
        ),
        migrations.RemoveIndex(
            model_name='z6_requestlog',
            name='varda_z6_re_vakajar_9ad3f4_idx',
        ),
        migrations.RemoveIndex(
            model_name='z6_requestlog',
            name='varda_z6_re_lahdeja_5bd86a_idx',
        ),
        migrations.RemoveIndex(
            model_name='z6_requestlog',
            name='varda_z6_re_user_id_0a04de_idx',
        ),
        migrations.AddIndex(
            model_name='z6_requestlog',
            index=models.Index(fields=['vakajarjestaja', 'timestamp'], name='varda_z6_re_vakajar_ec6c34_idx'),
        ),
        migrations.AddIndex(
            model_name='z6_requestlog',
            index=models.Index(fields=['vakajarjestaja', 'user', 'timestamp'], name='varda_z6_re_vakajar_a4bec5_idx'),
        ),
        migrations.AddIndex(
            model_name='z6_requestlog',
            index=models.Index(fields=['lahdejarjestelma', 'timestamp'], name='varda_z6_re_lahdeja_5d94c2_idx'),
        ),
        # Override autovacuum settings for z6_requestlog table.
        # https://www.postgresql.org/docs/14/runtime-config-autovacuum.html
        # autovacuum_vacuum_scale_factor = 0.025 -> run autovacuum when 2.5% of table is updated or deleted
        # autovacuum_analyze_scale_factor = 0.025 -> run autoanalyze when 2.5% of table is inserted, updated or deleted
        # autovacuum_vacuum_cost_limit = 1000 -> increase autovacuum performance (could be done globally)
        migrations.RunSQL(['ALTER TABLE varda_z6_requestlog SET (autovacuum_vacuum_scale_factor = 0.025);',
                           'ALTER TABLE varda_z6_requestlog SET (autovacuum_analyze_scale_factor = 0.025);',
                           'ALTER TABLE varda_z6_requestlog SET (autovacuum_vacuum_cost_limit = 1000);'],
                          reverse_sql='ALTER TABLE varda_z6_requestlog RESET (autovacuum_vacuum_scale_factor, '
                                      'autovacuum_analyze_scale_factor, autovacuum_vacuum_cost_limit);'),
    ]
