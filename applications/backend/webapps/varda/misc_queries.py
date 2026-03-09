import datetime
import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.cache import cache
from django.db import connections
from django.db.models import OuterRef, Q, Subquery
from django.db.models.functions import Lower
from django.utils import timezone
from guardian.shortcuts import get_objects_for_group
from psycopg import sql
from rest_framework.exceptions import APIException
from rest_framework.reverse import reverse

from varda.enums.koodistot import Koodistot
from varda.enums.organisaatiotyyppi import Organisaatiotyyppi
from varda.models import (
    Organisaatio,
    Lapsi,
    PaosOikeus,
    PaosToiminta,
    Toimipaikka,
    Z2_Code,
    Z4_CasKayttoOikeudet,
    Z9_RelatedObjectChanged,
)


logger = logging.getLogger(__name__)


def get_paos_toimipaikat(vakajarjestaja_obj, is_only_active_paostoiminta_included=True):
    tuottaja_organization_ids = PaosOikeus.objects.filter(jarjestaja_kunta_organisaatio=vakajarjestaja_obj).values_list(
        "tuottaja_organisaatio_id", flat=True
    )

    tuottaja_organizations_toimipaikka_ids = Toimipaikka.objects.filter(
        vakajarjestaja__id__in=tuottaja_organization_ids
    ).values_list("id", flat=True)
    paostoiminta_condition = Q(oma_organisaatio=vakajarjestaja_obj) & Q(
        paos_toimipaikka_id__in=tuottaja_organizations_toimipaikka_ids
    )

    # Get list of Toimipaikka IDs organization KATSELIJA group has permissions to just in case
    # (no other way to make sure two-way PAOS agreement has been established)
    if group := Group.objects.filter(name=f"{Z4_CasKayttoOikeudet.KATSELIJA}_{vakajarjestaja_obj.organisaatio_oid}").first():
        toimipaikka_permission_ids = get_objects_for_group(
            group, "varda.view_toimipaikka", accept_global_perms=False
        ).values_list("id", flat=True)
        paostoiminta_condition &= Q(paos_toimipaikka_id__in=toimipaikka_permission_ids)

    if is_only_active_paostoiminta_included:
        paostoiminta_condition &= Q(voimassa_kytkin=True)
    return PaosToiminta.objects.filter(paostoiminta_condition).values_list("paos_toimipaikka", flat=True)


def get_related_object_changed_id_qs(model_name, datetime_gt, datetime_lte, additional_filters=Q(), return_value="instance_id"):
    return (
        Z9_RelatedObjectChanged.objects.values("model_name", "instance_id", "trigger_model_name", "trigger_instance_id")
        .filter(
            Q(model_name=model_name)
            & Q(changed_timestamp__gt=datetime_gt)
            & Q(changed_timestamp__lte=datetime_lte)
            & additional_filters
        )
        .annotate(history_type_array=ArrayAgg("history_type", distinct=True))
        .exclude(history_type_array__contains=["+", "-"])
        .values_list(return_value, flat=True)
        .distinct()
    )


def _execute_yearly_report_query(
    cursor,
    query,
    params,
    format_args=(),
    return_dict=False,
    organisaatio_id=None,
    organisaatio_field_list=(),
    group_by_list=(),
    return_query_result=False,
):
    if organisaatio_id:
        organisaatio_filter_list = [f"{organisaatio_field} = %s" for organisaatio_field in organisaatio_field_list]
        query += f' AND ({" OR ".join(organisaatio_filter_list)})'
        params += [organisaatio_id] * len(organisaatio_field_list)
    if group_by_list:
        # PostgreSQL specific functionality (CUBE)
        query += f' GROUP BY CUBE ({", ".join(group_by_list)})'

    cursor.execute(sql.SQL(query).format(*format_args), params)

    if group_by_list or return_dict or return_query_result:
        result = cursor.fetchall()
        if return_query_result:
            return result

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
        row = cursor.fetchone()
        return row[0] if len(row) == 1 else row


def get_yearly_report_organisaatio_count(poiminta_pvm, tilasto_pvm):
    with connections[settings.READER_DB].cursor() as cursor:
        # PostgreSQL specific functionality (@> and ARRAY)
        cursor.execute(
            """
                SELECT count(id)
                FROM (
                    SELECT DISTINCT ON (id) * FROM varda_historicalorganisaatio
                    WHERE history_date <= %s ORDER BY id, history_date DESC
                ) org
                WHERE history_type != '-' AND alkamis_pvm <= %s AND
                    (paattymis_pvm >= %s OR paattymis_pvm IS NULL) AND organisaatiotyyppi::text[] @> ARRAY[%s];
            """,
            [poiminta_pvm, tilasto_pvm, tilasto_pvm, Organisaatiotyyppi.VAKAJARJESTAJA.value],
        )
        return cursor.fetchone()[0]


def get_yearly_report_toimipaikka_data(poiminta_pvm, tilasto_pvm, organisaatio_id):
    tm_codes = get_koodisto_codes_lower(Koodistot.toimintamuoto_koodit.value)
    tm_annotations = []
    format_args = []
    for tm_code in tm_codes:
        tm_annotations.append("COALESCE(SUM(CASE WHEN lower(toimintamuoto_koodi) = %s THEN 1 ELSE 0 END), 0) AS {}")
        format_args.append(sql.Identifier(tm_code))

    with connections[settings.READER_DB].cursor() as cursor:
        query = f"""
            SELECT count(id) AS toimipaikka_count,
            sum(varhaiskasvatuspaikat) AS varhaiskasvatuspaikat_sum, {', '.join(tm_annotations)}
            FROM (
                SELECT DISTINCT ON (id) * FROM varda_historicaltoimipaikka
                WHERE history_date <= %s ORDER BY id, history_date DESC
            ) tp
            WHERE history_type != '-' AND alkamis_pvm <= %s AND
                (paattymis_pvm >= %s OR paattymis_pvm IS NULL)
        """
        params = [*tm_codes, poiminta_pvm, tilasto_pvm, tilasto_pvm]
        organisaatio_field_list = ["vakajarjestaja_id"]

        return _execute_yearly_report_query(
            cursor,
            query,
            params,
            format_args=format_args,
            return_dict=True,
            organisaatio_id=organisaatio_id,
            organisaatio_field_list=organisaatio_field_list,
        )


def get_yearly_report_kielipainotus_data(poiminta_pvm, tilasto_pvm, organisaatio_id):
    kp_codes = get_koodisto_codes_lower(Koodistot.kielipainotustyyppi_koodit.value)
    kp_annotations = []
    for kp_code in kp_codes:
        kp_annotations.append(
            f"COALESCE(SUM(CASE WHEN lower(kielipainotustyyppi_koodi) = '{kp_code}' THEN 1 ELSE 0 END), 0) AS {kp_code}"
        )

    with connections[settings.READER_DB].cursor() as cursor:
        query = f"""
            SELECT count(kp.id) AS kielipainotus_count,
            {', '.join(kp_annotations)}
            FROM (
                SELECT DISTINCT ON (id) *
                FROM public.varda_historicalkielipainotus
                WHERE history_date <= '{poiminta_pvm}'
                ORDER BY id, history_date DESC
            ) kp
            JOIN (
                SELECT DISTINCT ON (id) *
                FROM public.varda_historicaltoimipaikka
                WHERE history_date <= '{poiminta_pvm}'
                ORDER BY id, history_date DESC
            ) tp
                ON tp.id = kp.toimipaikka_id
                AND tp.history_type != '-'
                AND tp.alkamis_pvm <= '{tilasto_pvm}'
                AND (tp.paattymis_pvm >= '{tilasto_pvm}' OR tp.paattymis_pvm IS NULL)
            WHERE
                kp.history_type != '-'
                AND kp.alkamis_pvm <= '{tilasto_pvm}'
                AND (kp.paattymis_pvm >= '{tilasto_pvm}' OR kp.paattymis_pvm IS NULL)
        """
        params = []
        organisaatio_field_list = ["vakajarjestaja_id"]

        return _execute_yearly_report_query(
            cursor,
            query,
            params,
            return_dict=True,
            organisaatio_id=organisaatio_id,
            organisaatio_field_list=organisaatio_field_list,
        )


def get_yearly_report_toimintakieli_data(poiminta_pvm, tilasto_pvm, organisaatio_id):
    with connections[settings.READER_DB].cursor() as cursor:
        vakajarjestaja_filter = f"AND tp.vakajarjestaja_id = {organisaatio_id}" if organisaatio_id else ""
        query = f"""
            SELECT
                UPPER(TRIM(k)) AS toimintakieli_koodi,
                COUNT(*) AS kieli_count
            FROM (
                SELECT DISTINCT ON (id) *
                FROM public.varda_historicaltoimipaikka
                WHERE history_date <= '{poiminta_pvm}'
                ORDER BY id, history_date DESC
            ) tp
            CROSS JOIN LATERAL unnest(tp.toimintakieli_koodi) AS k
            WHERE tp.history_type != '-'
                AND tp.alkamis_pvm <= '{tilasto_pvm}'
                AND (tp.paattymis_pvm >= '{tilasto_pvm}' OR tp.paattymis_pvm IS NULL)
                {vakajarjestaja_filter}
            GROUP BY UPPER(TRIM(k))
            ORDER BY kieli_count DESC, toimintakieli_koodi
        """
        params = []

        language_code_count_tuples = _execute_yearly_report_query(
            cursor,
            query,
            params,
            return_query_result=True,
        )
        return [dict(language_code=code[0], value=code[1]) for code in language_code_count_tuples]


def get_yearly_report_toiminnallinen_painotus_count(poiminta_pvm, tilasto_pvm, organisaatio_id):
    with connections[settings.READER_DB].cursor() as cursor:
        query = """
            SELECT count(tpa.id)
            FROM (
                SELECT DISTINCT ON (id) * FROM varda_historicaltoiminnallinenpainotus
                WHERE history_date <= %s ORDER BY id, history_date DESC
            ) tpa
            JOIN (
                SELECT DISTINCT ON (id) * FROM varda_historicaltoimipaikka
                WHERE history_date <= %s ORDER BY id, history_date DESC
            ) tp ON tp.id = tpa.toimipaikka_id AND tp.history_type != '-' AND tp.alkamis_pvm <= %s AND
                (tp.paattymis_pvm >= %s OR tp.paattymis_pvm IS NULL)
            WHERE tpa.history_type != '-' AND tpa.alkamis_pvm <= %s AND
                (tpa.paattymis_pvm >= %s OR tpa.paattymis_pvm IS NULL)
        """
        params = [poiminta_pvm, poiminta_pvm, tilasto_pvm, tilasto_pvm, tilasto_pvm, tilasto_pvm]
        organisaatio_field_list = ["vakajarjestaja_id"]

        return _execute_yearly_report_query(
            cursor, query, params, organisaatio_id=organisaatio_id, organisaatio_field_list=organisaatio_field_list
        )


def get_yearly_report_lapsi_ids(poiminta_pvm, tilasto_pvm, organisaatio_id):
    with connections[settings.READER_DB].cursor() as cursor:
        query = """
            SELECT
            array_agg(DISTINCT la.id) lapsi_id_array,
            array_agg(DISTINCT su.id) varhaiskasvatussuhde_id_array
            FROM (
                SELECT DISTINCT ON (id) * FROM varda_historicalvarhaiskasvatussuhde
                WHERE history_date <= %s ORDER BY id, history_date DESC
            ) su
            JOIN LATERAL (
                SELECT DISTINCT ON(id) * FROM varda_historicaltoimipaikka
                WHERE history_date <= %s AND id = su.toimipaikka_id ORDER BY id, history_date DESC
            ) tp ON tp.history_type != '-'
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicalvarhaiskasvatuspaatos
                WHERE history_date <= %s AND id = su.varhaiskasvatuspaatos_id ORDER BY id, history_date DESC
            ) pa ON pa.history_type != '-'
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicallapsi
                WHERE history_date <= %s AND id = pa.lapsi_id ORDER BY id, history_date DESC
            ) la ON la.history_type != '-'
            /* left join since varda_historicalhenkilo is not complete in test environments */
            LEFT JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicalhenkilo
                WHERE history_date <= %s AND id = la.henkilo_id ORDER BY id, history_date DESC
            ) he ON he.history_type != '-'
            WHERE su.history_type != '-' AND su.alkamis_pvm <= %s AND
                (su.paattymis_pvm >= %s OR su.paattymis_pvm IS NULL) AND
                pa.alkamis_pvm <= %s AND (pa.paattymis_pvm >= %s OR pa.paattymis_pvm IS NULL) AND
                tp.alkamis_pvm <= %s AND (tp.paattymis_pvm >= %s OR tp.paattymis_pvm IS NULL) AND
                (he.id IS NULL OR he.syntyma_pvm > %s - interval '11 years')
        """
        params = [
            poiminta_pvm,
            poiminta_pvm,
            poiminta_pvm,
            poiminta_pvm,
            poiminta_pvm,
            tilasto_pvm,
            tilasto_pvm,
            tilasto_pvm,
            tilasto_pvm,
            tilasto_pvm,
            tilasto_pvm,
            tilasto_pvm,
        ]
        organisaatio_field_list = ["la.vakatoimija_id", "la.oma_organisaatio_id", "la.paos_organisaatio_id"]

        return _execute_yearly_report_query(
            cursor,
            query,
            params,
            return_dict=True,
            organisaatio_id=organisaatio_id,
            organisaatio_field_list=organisaatio_field_list,
        )


def get_yearly_report_vaka_data(poiminta_pvm, varhaiskasvatussuhde_id_list):
    with connections[settings.READER_DB].cursor() as cursor:
        query = """
            SELECT
            CASE
                WHEN la.vakatoimija_id IS NOT NULL THEN false
                WHEN la.oma_organisaatio_id IS NOT NULL AND la.paos_organisaatio_id IS NOT NULL THEN true
                ELSE NULL
            END AS is_paos,
            lower(tp.toimintamuoto_koodi) AS toimintamuoto,
            count(DISTINCT su.id) AS suhde_count,
            count(DISTINCT pa.id) AS paatos_count,
            count(DISTINCT la.id) AS lapsi_count,
            count(DISTINCT la.henkilo_id) AS henkilo_count,
            count(DISTINCT la.id) filter(WHERE pa.vuorohoito_kytkin = true) AS vuorohoito_count,
            count(DISTINCT la.id) filter(WHERE pa.kokopaivainen_vaka_kytkin = false) AS osapaivainen_count,
            count(DISTINCT la.id) filter(WHERE pa.kokopaivainen_vaka_kytkin = true) AS kokopaivainen_count
            FROM (
                SELECT DISTINCT ON (id) * FROM varda_historicalvarhaiskasvatussuhde
                WHERE history_date <= %s AND id = ANY(%s)
                ORDER BY id, history_date DESC
            ) su
            JOIN LATERAL (
                SELECT DISTINCT ON(id) * FROM varda_historicaltoimipaikka
                WHERE history_date <= %s AND id = su.toimipaikka_id ORDER BY id, history_date DESC
            ) tp ON tp.history_type != '-'
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicalvarhaiskasvatuspaatos
                WHERE history_date <= %s AND id = su.varhaiskasvatuspaatos_id ORDER BY id, history_date DESC
            ) pa ON pa.history_type != '-'
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicallapsi
                WHERE history_date <= %s AND id = pa.lapsi_id ORDER BY id, history_date DESC
            ) la ON la.history_type != '-'
        """
        params = [poiminta_pvm, varhaiskasvatussuhde_id_list, poiminta_pvm, poiminta_pvm, poiminta_pvm]
        group_by_list = ["is_paos", "toimintamuoto"]

        return _execute_yearly_report_query(cursor, query, params, group_by_list=group_by_list)


def get_yearly_report_maksutieto_data(poiminta_pvm, tilasto_pvm, organisaatio_id, lapsi_id_list):
    with connections[settings.READER_DB].cursor() as cursor:
        query = """
            SELECT
            CASE
                WHEN la.vakatoimija_id IS NOT NULL THEN false
                WHEN la.oma_organisaatio_id IS NOT NULL AND la.paos_organisaatio_id IS NOT NULL THEN true
                ELSE NULL
            END AS is_paos,
            lower(ma.maksun_peruste_koodi) AS maksun_peruste,
            count(DISTINCT ma.id) AS count
            FROM (
                SELECT DISTINCT ON (id) * FROM varda_historicallapsi
                WHERE history_date <= %s AND id = ANY(%s)
                ORDER BY id, history_date DESC
            ) la
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicalhuoltajuussuhde
                WHERE history_date <= %s AND lapsi_id = la.id ORDER BY id, history_date DESC
            ) hu ON hu.history_type != '-'
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicalmaksutietohuoltajuussuhde
                WHERE history_date <= %s AND huoltajuussuhde_id = hu.id ORDER BY id, history_date DESC
            ) mahu ON mahu.history_type != '-'
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicalmaksutieto
                WHERE history_date <= %s AND id = mahu.maksutieto_id ORDER BY id, history_date DESC
            ) ma
            ON ma.history_type != '-' AND ma.alkamis_pvm <= %s AND (ma.paattymis_pvm >= %s OR ma.paattymis_pvm IS NULL)
        """
        params = [poiminta_pvm, lapsi_id_list, poiminta_pvm, poiminta_pvm, poiminta_pvm, tilasto_pvm, tilasto_pvm]
        # Get maksutieto data only if organisaatio_id is not paos_organisaatio of Lapsi
        organisaatio_field_list = ["la.vakatoimija_id", "la.oma_organisaatio_id"]
        group_by_list = ["is_paos", "maksun_peruste"]

        return _execute_yearly_report_query(
            cursor,
            query,
            params,
            organisaatio_id=organisaatio_id,
            organisaatio_field_list=organisaatio_field_list,
            group_by_list=group_by_list,
        )


def get_yearly_report_tyontekija_ids(poiminta_pvm, tilasto_pvm, organisaatio_id):
    with connections[settings.READER_DB].cursor() as cursor:
        query = """
            SELECT
            array_agg(DISTINCT pa.id) palvelussuhde_id_array,
            array_agg(DISTINCT tyo.id) tyoskentelypaikka_id_array
            FROM (
                SELECT DISTINCT ON (id) * FROM varda_historicaltyoskentelypaikka
                WHERE history_date <= %s ORDER BY id, history_date DESC
            ) tyo
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicalpalvelussuhde
                WHERE history_date <= %s AND id = tyo.palvelussuhde_id ORDER BY id, history_date DESC
            ) pa ON pa.history_type != '-'
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicaltyontekija
                WHERE history_date <= %s AND id = pa.tyontekija_id ORDER BY id, history_date DESC
            ) ty ON ty.history_type != '-'
            WHERE tyo.history_type != '-' AND
                tyo.alkamis_pvm <= %s AND (tyo.paattymis_pvm >= %s OR tyo.paattymis_pvm IS NULL) AND
                pa.alkamis_pvm <= %s AND (pa.paattymis_pvm >= %s OR pa.paattymis_pvm IS NULL) AND
                /* Filter out Palvelussuhde objects which have an active PidempiPoissaolo object */
                NOT EXISTS (
                    SELECT 1 FROM (
                        SELECT DISTINCT ON (id) * FROM varda_historicalpidempipoissaolo
                        WHERE history_date <= %s AND palvelussuhde_id = pa.id ORDER BY id, history_date DESC
                    ) pp
                    WHERE history_type != '-' AND alkamis_pvm <= %s AND paattymis_pvm >= %s
                )
        """
        params = [
            poiminta_pvm,
            poiminta_pvm,
            poiminta_pvm,
            tilasto_pvm,
            tilasto_pvm,
            tilasto_pvm,
            tilasto_pvm,
            poiminta_pvm,
            tilasto_pvm,
            tilasto_pvm,
        ]
        organisaatio_field_list = ["ty.vakajarjestaja_id"]

        return _execute_yearly_report_query(
            cursor,
            query,
            params,
            return_dict=True,
            organisaatio_id=organisaatio_id,
            organisaatio_field_list=organisaatio_field_list,
        )


def get_yearly_report_tyoskentelypaikka_data(poiminta_pvm, tyoskentelypaikka_id_list):
    with connections[settings.READER_DB].cursor() as cursor:
        query = """
            SELECT
            lower(tyo.tehtavanimike_koodi) AS tehtavanimike,
            count(DISTINCT ty.henkilo_id) AS henkilo_count,
            count(DISTINCT ty.henkilo_id) filter(WHERE tyo.kiertava_tyontekija_kytkin = true) AS henkilo_kiertava_count,
            count(DISTINCT ty.henkilo_id) filter(WHERE tyo.kelpoisuus_kytkin = true) AS henkilo_kelpoinen_count
            FROM (
                SELECT DISTINCT ON (id) * FROM varda_historicaltyoskentelypaikka
                WHERE history_date <= %s AND id = ANY(%s) ORDER BY id, history_date DESC
            ) tyo
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicalpalvelussuhde
                WHERE history_date <= %s AND id = tyo.palvelussuhde_id ORDER BY id, history_date DESC
            ) pa ON pa.history_type != '-'
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicaltyontekija
                WHERE history_date <= %s AND id = pa.tyontekija_id ORDER BY id, history_date DESC
            ) ty ON ty.history_type != '-'
        """
        params = [poiminta_pvm, tyoskentelypaikka_id_list, poiminta_pvm, poiminta_pvm]
        group_by_list = ["tehtavanimike"]

        return _execute_yearly_report_query(cursor, query, params, group_by_list=group_by_list)


def get_yearly_report_palvelussuhde_data(poiminta_pvm, palvelussuhde_id_list):
    with connections[settings.READER_DB].cursor() as cursor:
        query = """
            SELECT
            lower(pa.tyosuhde_koodi) AS tyosuhde,
            lower(pa.tyoaika_koodi) AS tyoaika,
            count(DISTINCT pa.id) AS palvelussuhde_count
            FROM (
                SELECT DISTINCT ON (id) * FROM varda_historicalpalvelussuhde
                WHERE history_date <= %s AND id = ANY(%s) ORDER BY id, history_date DESC
            ) pa
        """
        params = [poiminta_pvm, palvelussuhde_id_list]
        group_by_list = ["tyosuhde", "tyoaika"]

        return _execute_yearly_report_query(cursor, query, params, group_by_list=group_by_list)


def get_yearly_report_tyontekija_multiple_tehtavanimike_count(poiminta_pvm, tyoskentelypaikka_id_list):
    with connections[settings.READER_DB].cursor() as cursor:
        query = """
            SELECT count(henkilo_id)
            FROM (
                SELECT ty.henkilo_id
                FROM (
                    SELECT DISTINCT ON (id) * FROM varda_historicaltyoskentelypaikka
                    WHERE history_date <= %s AND id = ANY(%s) ORDER BY id, history_date DESC
                ) tyo
                JOIN LATERAL (
                    SELECT DISTINCT ON (id) * FROM varda_historicalpalvelussuhde
                    WHERE history_date <= %s AND id = tyo.palvelussuhde_id ORDER BY id, history_date DESC
                ) pa ON pa.history_type != '-'
                JOIN LATERAL (
                    SELECT DISTINCT ON (id) * FROM varda_historicaltyontekija
                    WHERE history_date <= %s AND id = pa.tyontekija_id ORDER BY id, history_date DESC
                ) ty ON ty.history_type != '-'
                GROUP BY ty.henkilo_id
                HAVING count(DISTINCT lower(tyo.tehtavanimike_koodi)) > 1
            ) sq
        """
        params = [poiminta_pvm, tyoskentelypaikka_id_list, poiminta_pvm, poiminta_pvm]

        return _execute_yearly_report_query(cursor, query, params)


def get_yearly_report_taydennyskoulutus_data(poiminta_pvm, tilasto_pvm, tyoskentelypaikka_id_list):
    with connections[settings.READER_DB].cursor() as cursor:
        query = """
            SELECT
            lower(ty.tehtavanimike_koodi) AS tehtavanimike,
            count(DISTINCT ty.henkilo_id) AS henkilo_count,
            sum(ta.koulutuspaivia) AS koulutuspaiva_sum
            FROM (
                /* Get unique henkilo_id and tehtavanimike_koodi pairs so we do not get extra Taydennyskoulutus rows */
                SELECT DISTINCT ON (sq_ty.henkilo_id, tyo.tehtavanimike_koodi)
                    sq_ty.henkilo_id AS henkilo_id, sq_ty.id AS tyontekija_id, tyo.tehtavanimike_koodi
                FROM (
                    SELECT DISTINCT ON (id) * FROM varda_historicaltyoskentelypaikka
                    WHERE history_date <= %s AND id = ANY(%s) ORDER BY id, history_date DESC
                ) tyo
                JOIN LATERAL (
                    SELECT DISTINCT ON (id) * FROM varda_historicalpalvelussuhde
                    WHERE history_date <= %s AND id = tyo.palvelussuhde_id ORDER BY id, history_date DESC
                ) pa ON pa.history_type != '-'
                JOIN LATERAL (
                    SELECT DISTINCT ON (id) * FROM varda_historicaltyontekija
                    WHERE history_date <= %s AND id = pa.tyontekija_id ORDER BY id, history_date DESC
                ) sq_ty ON sq_ty.history_type != '-'
            ) ty
            JOIN LATERAL (
                /* Associate Tyontekija object only once per Taydennyskoulutus */
                SELECT DISTINCT ON (sq_taty.tyontekija_id, sq_taty.taydennyskoulutus_id) *
                FROM (
                    SELECT DISTINCT ON (id) * FROM varda_historicaltaydennyskoulutustyontekija
                    WHERE history_date <= %s AND tyontekija_id = ty.tyontekija_id ORDER BY id, history_date DESC
                ) sq_taty
                WHERE sq_taty.history_type != '-'
            ) taty ON true
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicaltaydennyskoulutus
                WHERE history_date <= %s AND id = taty.taydennyskoulutus_id ORDER BY id, history_date DESC
            ) ta ON ta.history_type != '-'
            WHERE taty.history_type != '-' AND date_part('year', ta.suoritus_pvm) = %s
        """
        params = [
            poiminta_pvm,
            tyoskentelypaikka_id_list,
            poiminta_pvm,
            poiminta_pvm,
            poiminta_pvm,
            poiminta_pvm,
            tilasto_pvm.year,
        ]
        group_by_list = ["tehtavanimike"]

        return _execute_yearly_report_query(cursor, query, params, group_by_list=group_by_list)


def get_yearly_report_vuokrattu_henkilosto_data(poiminta_pvm, tilasto_pvm, organisaatio_id):
    with connections[settings.READER_DB].cursor() as cursor:
        query = """
            SELECT COALESCE(sum(tyontekijamaara), 0), COALESCE(sum(tuntimaara), 0)
            FROM (
                SELECT DISTINCT ON (id) * FROM varda_historicalvuokrattuhenkilosto
                WHERE history_date <= %s ORDER BY id, history_date DESC
            ) sq
            WHERE history_type != '-' AND date_part('year', kuukausi) = %s
        """
        params = [poiminta_pvm, tilasto_pvm.year]
        organisaatio_field_list = ["vakajarjestaja_id"]

        return _execute_yearly_report_query(
            cursor, query, params, organisaatio_id=organisaatio_id, organisaatio_field_list=organisaatio_field_list
        )


def get_yearly_report_fixed_term_data(poiminta_pvm, year, month, organisaatio_id):
    # Almost identical with get_yearly_report_tyontekija_ids, but without PidempiPoissaolo
    if month:
        alkamis_pvm_lt = datetime.date(year, month + 1, 1) if month != 12 else datetime.date(year + 1, 1, 1)
        paattymis_pvm_gte = datetime.date(year, month, 1)
    else:
        # Get whole year
        alkamis_pvm_lt = datetime.date(year + 1, 1, 1)
        paattymis_pvm_gte = datetime.date(year, 1, 1)

    with connections[settings.READER_DB].cursor() as cursor:
        query = """
            SELECT count(DISTINCT ty.henkilo_id) AS henkilo_count
            FROM (
                SELECT DISTINCT ON (id) * FROM varda_historicaltyoskentelypaikka
                WHERE history_date <= %s ORDER BY id, history_date DESC
            ) tyo
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicalpalvelussuhde
                WHERE history_date <= %s AND id = tyo.palvelussuhde_id ORDER BY id, history_date DESC
            ) pa ON pa.history_type != '-'
            JOIN LATERAL (
                SELECT DISTINCT ON (id) * FROM varda_historicaltyontekija
                WHERE history_date <= %s AND id = pa.tyontekija_id ORDER BY id, history_date DESC
            ) ty ON ty.history_type != '-'
            WHERE pa.tyosuhde_koodi = '2' AND tyo.history_type != '-' AND
                tyo.alkamis_pvm < %s AND (tyo.paattymis_pvm >= %s OR tyo.paattymis_pvm IS NULL) AND
                pa.alkamis_pvm < %s AND (pa.paattymis_pvm >= %s OR pa.paattymis_pvm IS NULL)
        """
        params = [poiminta_pvm, poiminta_pvm, poiminta_pvm, alkamis_pvm_lt, paattymis_pvm_gte, alkamis_pvm_lt, paattymis_pvm_gte]
        organisaatio_field_list = ["ty.vakajarjestaja_id"]

        return _execute_yearly_report_query(
            cursor, query, params, organisaatio_id=organisaatio_id, organisaatio_field_list=organisaatio_field_list
        )


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
    from varda.cache import get_object_ids_user_has_permissions
    from varda.permissions import is_oph_staff, user_permission_groups_in_organizations

    items_to_show = 3
    user = request.user
    queryset_model_name = queryset.model.__name__.lower()

    permission_group_qs = user_permission_groups_in_organizations(user, oid_list, permission_group_list)
    if not user.is_superuser and not is_oph_staff(user) and not permission_group_qs.exists():
        # User is not superuser, OPH user and does not belong to correct permission groups
        id_list = get_object_ids_user_has_permissions(user, queryset.model)
        queryset = queryset.filter(id__in=id_list)
    queryset = queryset.order_by("id")[:items_to_show].values("pk")
    return [
        reverse(viewname=f"{queryset_model_name}-detail", kwargs={"pk": instance["pk"]}, request=request) for instance in queryset
    ]


def get_history_value_subquery(model, field_name, datetime_param):
    return Subquery(
        model.history.filter(id=OuterRef("id"), history_date__lte=datetime_param)
        .distinct("id")
        .order_by("id", "-history_date")
        .values(field_name)
    )


def get_active_filter(target_date, target_date_secondary=None, prefix=""):
    """
    Get Q filter for getting only objects that are currently active. Optionally use prefix to filter on related data.
    :param target_date: Date object
    :param target_date_secondary: Date object, used for paattymis_pvm if given
    :param prefix: string, e.g. varhaiskasvatuspaatokset (__ added automatically)
    :return: Q object filter
    """
    if prefix and not prefix.endswith("__"):
        prefix += "__"
    return Q(**{f"{prefix}alkamis_pvm__lte": target_date}) & (
        Q(**{f"{prefix}paattymis_pvm__gte": target_date_secondary or target_date}) | Q(**{f"{prefix}paattymis_pvm__isnull": True})
    )


def get_active_vakajarjestajat():
    now = timezone.now()
    return Organisaatio.vakajarjestajat.filter(get_active_filter(now)).order_by("id")


def get_tallentaja_organisaatio_oid_for_paos_lapsi(lapsi):
    """
    Get organisaatio_oid of Organisaatio that is responsible for saving data of PAOS lapsi
    :param lapsi: Lapsi instance
    :return: organisaatio_oid of Organisaatio
    """
    paos_oikeus = PaosOikeus.objects.filter(
        jarjestaja_kunta_organisaatio=lapsi.oma_organisaatio, tuottaja_organisaatio=lapsi.paos_organisaatio, voimassa_kytkin=True
    ).first()
    return paos_oikeus.tallentaja_organisaatio.organisaatio_oid if paos_oikeus else None


def get_lapsi_for_maksutieto(maksutieto):
    """
    Get Lapsi object instance that is related to provided Maksutieto object
    :param maksutieto: Maksutieto instance
    :return: Lapsi instance
    """
    lapsi_qs = maksutieto.huoltajuussuhteet.values_list("lapsi_id", flat=True).distinct("lapsi_id").order_by("lapsi_id")
    if lapsi_qs.count() != 1:
        logger.error(f"Could not find just one related Lapsi object for Maksutieto with ID: {maksutieto.id}")
        raise APIException
    return Lapsi.objects.get(id=lapsi_qs.first())


def get_organisaatio_oid_for_taydennyskoulutus(taydennyskoulutus):
    """
    Get organisaatio_oid of Organisaatio that is related to provided Taydennyskoulutus object
    :param taydennyskoulutus: Taydennyskoulutus instance
    :return: organisaatio_oid of Organisaatio
    """
    vakajarjestaja_oid_qs = (
        taydennyskoulutus.tyontekijat.values_list("vakajarjestaja__organisaatio_oid", flat=True)
        .distinct("vakajarjestaja__organisaatio_oid")
        .order_by("vakajarjestaja__organisaatio_oid")
    )
    if len(vakajarjestaja_oid_qs) != 1:
        logger.error(f"Could not find just one related Organisaatio for Taydennyskoulutus with ID: {taydennyskoulutus.id}")
        raise APIException
    return vakajarjestaja_oid_qs.first()


def get_koodisto_codes_lower(koodisto_name):
    return (
        Z2_Code.objects.filter(koodisto__name=koodisto_name)
        .annotate(code_lower=Lower("code_value"))
        .values_list("code_lower", flat=True)
        .order_by("code_lower")
    )


def get_tuentaso_codes_by_tilastointi_pvm(tilastointi_pvm):
    return list(
        Z2_Code.objects.filter(
            Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gte=tilastointi_pvm),
            alkamis_pvm__lte=tilastointi_pvm,
            koodisto__name=Koodistot.tuentaso_koodit.value,
        )
        .order_by("code_value")
        .values_list("code_value", flat=True)
    )


def get_ikaryhma_codes_by_tilastointi_pvm(tilastointi_pvm):
    return list(
        Z2_Code.objects.filter(
            Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gte=tilastointi_pvm),
            alkamis_pvm__lte=tilastointi_pvm,
            koodisto__name=Koodistot.ikaryhma_koodit.value,
        )
        .order_by("code_value")
        .values_list("code_value", flat=True)
    )


def get_queryset_count(queryset, queryset_count_cache_key):
    """
    :param queryset:
    :param queryset_count_cache_key: If None, simply return the queryset.count() without utilizing cache.
    :return:
    """
    try:
        if queryset_count_cache_key:
            cached_count = cache.get(queryset_count_cache_key)
            if cached_count is not None:
                return cached_count

        count = queryset.count()

        if queryset_count_cache_key:
            cache.set(queryset_count_cache_key, count, timeout=300)  # Cache for 5 minutes
        return count

    except Exception:
        logger.error(f"Fetching cache failed: {queryset_count_cache_key}")

    return queryset.count()
