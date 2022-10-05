import logging

from django.contrib.auth.models import Group
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import connection
from django.db.models import OuterRef, Q, Subquery
from django.db.models.functions import Lower
from guardian.shortcuts import get_objects_for_group
from psycopg2 import sql
from rest_framework.exceptions import APIException
from rest_framework.reverse import reverse

from varda.enums.koodistot import Koodistot
from varda.enums.organisaatiotyyppi import Organisaatiotyyppi
from varda.models import (Lapsi, PaosOikeus, PaosToiminta, Toimipaikka, Z2_Code, Z4_CasKayttoOikeudet,
                          Z9_RelatedObjectChanged)


logger = logging.getLogger(__name__)


def get_paos_toimipaikat(vakajarjestaja_obj, is_only_active_paostoiminta_included=True):
    tuottaja_organization_ids = (PaosOikeus.objects.filter(jarjestaja_kunta_organisaatio=vakajarjestaja_obj)
                                 .values_list('tuottaja_organisaatio_id', flat=True))

    tuottaja_organizations_toimipaikka_ids = (Toimipaikka.objects
                                              .filter(vakajarjestaja__id__in=tuottaja_organization_ids)
                                              .values_list('id', flat=True))
    paostoiminta_condition = Q(oma_organisaatio=vakajarjestaja_obj) & Q(paos_toimipaikka_id__in=tuottaja_organizations_toimipaikka_ids)

    # Get list of Toimipaikka IDs organization KATSELIJA group has permissions to just in case
    # (no other way to make sure two-way PAOS agreement has been established)
    if group := Group.objects.filter(name=f'{Z4_CasKayttoOikeudet.KATSELIJA}_{vakajarjestaja_obj.organisaatio_oid}').first():
        toimipaikka_permission_ids = (get_objects_for_group(group, 'varda.view_toimipaikka', accept_global_perms=False)
                                      .values_list('id', flat=True))
        paostoiminta_condition &= Q(paos_toimipaikka_id__in=toimipaikka_permission_ids)

    if is_only_active_paostoiminta_included:
        paostoiminta_condition &= Q(voimassa_kytkin=True)
    return PaosToiminta.objects.filter(paostoiminta_condition).values_list('paos_toimipaikka', flat=True)


def get_related_object_changed_id_qs(model_name, datetime_gt, datetime_lte, additional_filters=None,
                                     return_value='instance_id'):
    additional_filters = additional_filters or {}
    return (Z9_RelatedObjectChanged.objects
            .values('model_name', 'instance_id', 'trigger_model_name', 'trigger_instance_id')
            .filter(model_name=model_name, changed_timestamp__gt=datetime_gt, changed_timestamp__lte=datetime_lte,
                    **additional_filters)
            .annotate(history_type_array=ArrayAgg('history_type', distinct=True))
            .exclude(history_type_array__contains=['+', '-'])
            .values_list(return_value, flat=True).distinct())


def _execute_yearly_report_query(cursor, query, params, format_args=(), organisaatio_id=None,
                                 organisaatio_field_list=(), group_by_list=None):
    if organisaatio_id:
        organisaatio_filter_list = [f'{organisaatio_field} = %s' for organisaatio_field in organisaatio_field_list]
        query += f' AND ({" OR ".join(organisaatio_filter_list)})'
        params += [organisaatio_id] * len(organisaatio_field_list)
    if group_by_list:
        # PostgreSQL specific functionality (CUBE)
        query += f' GROUP BY CUBE ({", ".join(group_by_list)})'

    cursor.execute(sql.SQL(query).format(*format_args), params)

    if group_by_list is not None:
        result = cursor.fetchall()

        # Create a nested dict for easy value access
        result_dict = {}
        for row in result:
            temp_dict = result_dict
            for index, value in enumerate(row):
                if index < len(group_by_list):
                    # Create or get top level dict according to group by clause
                    new_dict = temp_dict.get(row[index], {})
                    temp_dict[row[index]] = new_dict
                    temp_dict = new_dict
                else:
                    # Create last dict with values
                    temp_dict[cursor.description[index][0]] = value
        return result_dict
    else:
        return cursor.fetchone()[0]


def get_yearly_report_organisaatio_count(poiminta_pvm, tilasto_pvm):
    with connection.cursor() as cursor:
        # PostgreSQL specific functionality (@> and ARRAY)
        cursor.execute('''
                SELECT count(id) FROM
                (SELECT DISTINCT ON (id) * FROM varda_historicalorganisaatio
                    WHERE history_date <= %s ORDER BY id, history_date DESC) org
                WHERE history_type != '-' AND alkamis_pvm <= %s AND
                    (paattymis_pvm >= %s OR paattymis_pvm IS NULL) AND organisaatiotyyppi::text[] @> ARRAY[%s];
            ''', [poiminta_pvm, tilasto_pvm, tilasto_pvm, Organisaatiotyyppi.VAKAJARJESTAJA.value])
        return cursor.fetchone()[0]


def get_yearly_report_toimipaikka_data(poiminta_pvm, tilasto_pvm, organisaatio_id):
    tm_codes = (Z2_Code.objects
                .filter(koodisto__name=Koodistot.toimintamuoto_koodit.value)
                .annotate(code_lower=Lower('code_value'))
                .values_list('code_lower', flat=True).order_by('code_lower'))
    tm_annotations = ''
    format_args = []
    for tm_code in tm_codes:
        tm_annotations += ", COALESCE(SUM(CASE WHEN lower(toimintamuoto_koodi) = %s THEN 1 ELSE 0 END), 0) AS {}"
        format_args.append(sql.Identifier(tm_code))

    with connection.cursor() as cursor:
        query = f'''
            SELECT count(id) AS toimipaikka_count,
            sum(varhaiskasvatuspaikat) AS varhaiskasvatuspaikat_sum{tm_annotations} FROM
            (SELECT DISTINCT ON (id) * FROM varda_historicaltoimipaikka
                WHERE history_date <= %s ORDER BY id, history_date DESC) tp
            WHERE history_type != '-' AND alkamis_pvm <= %s AND
                (paattymis_pvm >= %s OR paattymis_pvm IS NULL)
        '''
        params = [*tm_codes, poiminta_pvm, tilasto_pvm, tilasto_pvm]

        return _execute_yearly_report_query(cursor, query, params, format_args=format_args,
                                            organisaatio_id=organisaatio_id, group_by_list=(),
                                            organisaatio_field_list=['vakajarjestaja_id'])


def get_yearly_report_kielipainotus_count(poiminta_pvm, tilasto_pvm, organisaatio_id):
    with connection.cursor() as cursor:
        query = '''
            SELECT count(kp.id) FROM
            (SELECT DISTINCT ON (id) * FROM varda_historicalkielipainotus
                WHERE history_date <= %s ORDER BY id, history_date DESC) kp
            JOIN
            (SELECT DISTINCT ON (id) * FROM varda_historicaltoimipaikka
                WHERE history_date <= %s ORDER BY id, history_date DESC) tp
            ON tp.id = kp.toimipaikka_id AND tp.history_type != '-' AND tp.alkamis_pvm <= %s AND
                (tp.paattymis_pvm >= %s OR tp.paattymis_pvm IS NULL)
            WHERE kp.history_type != '-' AND kp.alkamis_pvm <= %s AND
                (kp.paattymis_pvm >= %s OR kp.paattymis_pvm IS NULL)
        '''
        params = [poiminta_pvm, poiminta_pvm, tilasto_pvm, tilasto_pvm, tilasto_pvm, tilasto_pvm]

        return _execute_yearly_report_query(cursor, query, params, organisaatio_id=organisaatio_id,
                                            organisaatio_field_list=['vakajarjestaja_id'])


def get_yearly_report_toiminnallinen_painotus_count(poiminta_pvm, tilasto_pvm, organisaatio_id):
    with connection.cursor() as cursor:
        query = '''
            SELECT count(tpa.id) FROM
            (SELECT DISTINCT ON (id) * FROM varda_historicaltoiminnallinenpainotus
                WHERE history_date <= %s ORDER BY id, history_date DESC) tpa
            JOIN
            (SELECT DISTINCT ON (id) * FROM varda_historicaltoimipaikka
                WHERE history_date <= %s ORDER BY id, history_date DESC) tp
            ON tp.id = tpa.toimipaikka_id AND tp.history_type != '-' AND tp.alkamis_pvm <= %s AND
                (tp.paattymis_pvm >= %s OR tp.paattymis_pvm IS NULL)
            WHERE tpa.history_type != '-' AND tpa.alkamis_pvm <= %s AND
                (tpa.paattymis_pvm >= %s OR tpa.paattymis_pvm IS NULL)
        '''
        params = [poiminta_pvm, poiminta_pvm, tilasto_pvm, tilasto_pvm, tilasto_pvm, tilasto_pvm]

        return _execute_yearly_report_query(cursor, query, params, organisaatio_id=organisaatio_id,
                                            organisaatio_field_list=['vakajarjestaja_id'])


def get_yearly_report_vaka_data(poiminta_pvm, tilasto_pvm, organisaatio_id):
    # In Vipunen Lapsi has to be under 11 years old and Varhaiskasvatussuhde related Toimipaikka, and Lapsi related
    # Organisaatio objects must be active, but let's simplify here because they are edge cases and make the query
    # too heavy
    with connection.cursor() as cursor:
        query = '''
            SELECT
            CASE
                WHEN la.vakatoimija_id IS NOT NULL THEN false
                WHEN la.oma_organisaatio_id IS NOT NULL AND la.paos_organisaatio_id IS NOT NULL THEN true
                ELSE NULL
            END AS is_paos,
            pa.vuorohoito_kytkin AS vuorohoito,
            count(DISTINCT su.id) AS suhde_count,
            count(DISTINCT pa.id) AS paatos_count,
            count(DISTINCT la.id) AS lapsi_count,
            count(DISTINCT la.henkilo_id) AS henkilo_count
            FROM
            (SELECT DISTINCT ON (id) * FROM varda_historicalvarhaiskasvatussuhde
                WHERE history_date <= %s ORDER BY id, history_date DESC) su
            JOIN
            (SELECT DISTINCT ON (id) * FROM varda_historicalvarhaiskasvatuspaatos
                WHERE history_date <= %s ORDER BY id, history_date DESC) pa
            ON pa.id = su.varhaiskasvatuspaatos_id AND pa.history_type != '-'
            JOIN
            (SELECT DISTINCT ON (id) * FROM varda_historicallapsi
                WHERE history_date <= %s ORDER BY id, history_date DESC) la
            ON la.id = pa.lapsi_id AND la.history_type != '-'
            WHERE su.history_type != '-' AND su.alkamis_pvm <= %s AND
                (su.paattymis_pvm >= %s OR su.paattymis_pvm IS NULL) AND
                pa.alkamis_pvm <= %s AND (pa.paattymis_pvm >= %s OR pa.paattymis_pvm IS NULL)
        '''
        params = [poiminta_pvm, poiminta_pvm, poiminta_pvm, tilasto_pvm, tilasto_pvm, tilasto_pvm, tilasto_pvm]
        organisaatio_field_list = ['la.vakatoimija_id', 'la.oma_organisaatio_id', 'la.paos_organisaatio_id']
        group_by_list = ['is_paos', 'vuorohoito']

        return _execute_yearly_report_query(cursor, query, params, organisaatio_id=organisaatio_id,
                                            organisaatio_field_list=organisaatio_field_list,
                                            group_by_list=group_by_list)


def get_yearly_report_maksutieto_data(poiminta_pvm, tilasto_pvm, organisaatio_id):
    # In Vipunen Lapsi has to be under 11 years old and Varhaiskasvatussuhde related Toimipaikka, and Lapsi related
    # Organisaatio objects must be active, and Lapsi has to have an active Varhaisaksvatuspaatos with an active
    # Varhaiskasvatussuhde, but let's simplify here because they are edge cases and make the query too heavy
    with connection.cursor() as cursor:
        query = '''
            SELECT
            CASE
                WHEN la.vakatoimija_id IS NOT NULL THEN false
                WHEN la.oma_organisaatio_id IS NOT NULL AND la.paos_organisaatio_id IS NOT NULL THEN true
                ELSE NULL
            END AS is_paos,
            lower(ma.maksun_peruste_koodi) as maksun_peruste,
            count(DISTINCT ma.id) AS maksutieto_count
            FROM
            (SELECT DISTINCT ON (id) * FROM varda_historicalmaksutieto
                WHERE history_date <= %s ORDER BY id, history_date DESC) ma
            JOIN
            (SELECT DISTINCT ON (id) * FROM varda_historicalmaksutietohuoltajuussuhde
                WHERE history_date <= %s ORDER BY id, history_date DESC) mahu
            ON mahu.maksutieto_id = ma.id AND mahu.history_type != '-'
            JOIN
            (SELECT DISTINCT ON (id) * FROM varda_historicalhuoltajuussuhde
                WHERE history_date <= %s ORDER BY id, history_date DESC) hu
            ON hu.id = mahu.huoltajuussuhde_id AND hu.history_type != '-'
            JOIN
            (SELECT DISTINCT ON (id) * FROM varda_historicallapsi
                WHERE history_date <= %s ORDER BY id, history_date DESC) la
            ON la.id = hu.lapsi_id AND la.history_type != '-'
            WHERE ma.history_type != '-' AND ma.alkamis_pvm <= %s AND
                (ma.paattymis_pvm >= %s OR ma.paattymis_pvm IS NULL)
        '''
        params = [poiminta_pvm, poiminta_pvm, poiminta_pvm, poiminta_pvm, tilasto_pvm, tilasto_pvm]
        organisaatio_field_list = ['la.vakatoimija_id', 'la.oma_organisaatio_id', 'la.paos_organisaatio_id']
        group_by_list = ['is_paos', 'maksun_peruste']

        return _execute_yearly_report_query(cursor, query, params, organisaatio_id=organisaatio_id,
                                            organisaatio_field_list=organisaatio_field_list,
                                            group_by_list=group_by_list)


def get_top_results(request, queryset, permission_group_list, oid_list):
    """
    Function that returns limited amount of results from a queryset based on user permissions. Used for x_top fields.
    :param request: request object
    :param queryset: base queryset
    :param permission_group_list: List of accepted permission groups (Z4_CasKayttoOikeudet values)
    :param oid_list: list of accepted OIDs (e.g. Organisaatio, Toimipaikka)
    :return: List of object URIs
    """
    # Import locally to avoid circular import
    from varda.cache import get_object_ids_for_user_by_model
    from varda.permissions import is_oph_staff, user_permission_groups_in_organizations

    items_to_show = 3
    user = request.user
    queryset_model_name = queryset.model.__name__.lower()

    permission_group_qs = user_permission_groups_in_organizations(user, oid_list, permission_group_list)
    if not user.is_superuser and not is_oph_staff(user) and not permission_group_qs.exists():
        # User is not superuser, OPH user and does not belong to correct permission groups
        id_list = get_object_ids_for_user_by_model(user, queryset_model_name)
        queryset = queryset.filter(id__in=id_list)
    queryset = queryset.order_by('id')[:items_to_show].values('pk')
    return [reverse(viewname=f'{queryset_model_name}-detail', kwargs={'pk': instance['pk']}, request=request)
            for instance in queryset]


def get_history_value_subquery(model, field_name, datetime_param):
    return Subquery(model.history.filter(id=OuterRef('id'), history_date__lte=datetime_param)
                    .distinct('id').order_by('id', '-history_date').values(field_name))


def get_active_filter(target_date, prefix=''):
    """
    Get Q filter for getting only objects that are currently active. Optionally use prefix to filter on related data.
    :param target_date: Date object
    :param prefix: string, e.g. varhaiskasvatuspaatokset (__ added automatically)
    :return: Q object filter
    """
    if prefix and not prefix.endswith('__'):
        prefix += '__'
    return (Q(**{f'{prefix}alkamis_pvm__lte': target_date}) &
            (Q(**{f'{prefix}paattymis_pvm__gte': target_date}) | Q(**{f'{prefix}paattymis_pvm__isnull': True})))


def get_tallentaja_organisaatio_oid_for_paos_lapsi(lapsi):
    """
    Get organisaatio_oid of Organisaatio that is responsible for saving data of PAOS lapsi
    :param lapsi: Lapsi instance
    :return: organisaatio_oid of Organisaatio
    """
    paos_oikeus = (PaosOikeus.objects
                   .filter(jarjestaja_kunta_organisaatio=lapsi.oma_organisaatio,
                           tuottaja_organisaatio=lapsi.paos_organisaatio, voimassa_kytkin=True)
                   .first())
    return paos_oikeus.tallentaja_organisaatio.organisaatio_oid if paos_oikeus else None


def get_lapsi_for_maksutieto(maksutieto):
    """
    Get Lapsi object instance that is related to provided Maksutieto object
    :param maksutieto: Maksutieto instance
    :return: Lapsi instance
    """
    lapsi_qs = maksutieto.huoltajuussuhteet.values_list('lapsi_id', flat=True).distinct('lapsi_id').order_by('lapsi_id')
    if lapsi_qs.count() != 1:
        logger.error(f'Could not find just one related Lapsi object for Maksutieto with ID: {maksutieto.id}')
        raise APIException
    return Lapsi.objects.get(id=lapsi_qs.first())


def get_organisaatio_oid_for_taydennyskoulutus(taydennyskoulutus):
    """
    Get organisaatio_oid of Organisaatio that is related to provided Taydennyskoulutus object
    :param taydennyskoulutus: Taydennyskoulutus instance
    :return: organisaatio_oid of Organisaatio
    """
    vakajarjestaja_oid_qs = (taydennyskoulutus.tyontekijat.values_list('vakajarjestaja__organisaatio_oid', flat=True)
                             .distinct('vakajarjestaja__organisaatio_oid').order_by('vakajarjestaja__organisaatio_oid'))
    if len(vakajarjestaja_oid_qs) != 1:
        logger.error(f'Could not find just one related Organisaatio for Taydennyskoulutus with ID: {taydennyskoulutus.id}')
        raise APIException
    return vakajarjestaja_oid_qs.first()
