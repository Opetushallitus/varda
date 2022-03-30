from django.contrib.postgres.aggregates import StringAgg
from django.db import connection
from django.db.models import OuterRef, Q, Subquery, Value
from rest_framework.reverse import reverse

from varda.cache import get_object_ids_for_user_by_model
from varda.models import (Henkilo, KieliPainotus, Lapsi, PaosOikeus, PaosToiminta, Toimipaikka, ToiminnallinenPainotus,
                          Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Z9_RelatedObjectChanged)
from varda.permissions import is_oph_staff, user_permission_groups_in_organizations


def get_paos_toimipaikat(vakajarjestaja_obj, is_only_active_paostoiminta_included=True):
    tuottaja_organization_ids = (PaosOikeus
                                 .objects
                                 .filter(jarjestaja_kunta_organisaatio=vakajarjestaja_obj)
                                 .values_list('tuottaja_organisaatio__id', flat=True))

    tuottaja_organizations_toimipaikka_ids = (Toimipaikka
                                              .objects
                                              .filter(vakajarjestaja__id__in=tuottaja_organization_ids)
                                              .values_list('id', flat=True))
    paostoiminta_condition = Q(oma_organisaatio=vakajarjestaja_obj) & Q(paos_toimipaikka__id__in=tuottaja_organizations_toimipaikka_ids)
    if is_only_active_paostoiminta_included:
        paostoiminta_condition = paostoiminta_condition & Q(voimassa_kytkin=True)
    return (PaosToiminta
            .objects
            .filter(paostoiminta_condition)
            .values_list('paos_toimipaikka', flat=True))


def get_related_object_changed_id_qs(model_name, datetime_gt, datetime_lte, additional_filters=None,
                                     return_value='instance_id'):
    additional_filters = additional_filters or {}
    return (Z9_RelatedObjectChanged.objects
            .values('model_name', 'instance_id', 'trigger_model_name', 'trigger_instance_id')
            .filter(model_name=model_name, changed_timestamp__gt=datetime_gt, changed_timestamp__lte=datetime_lte,
                    **additional_filters)
            .annotate(history_type_list=StringAgg('history_type', ',', default=Value('')))
            .filter(~(Q(history_type_list__contains='+') & Q(history_type_list__contains='-')))
            .values_list(return_value, flat=True).distinct())


def get_vakajarjestaja_is_active(vakajarjestaja, tilasto_pvm, full_query):
    if full_query:
        return True
    if vakajarjestaja.paattymis_pvm is None:
        return vakajarjestaja.alkamis_pvm <= tilasto_pvm
    return vakajarjestaja.alkamis_pvm <= tilasto_pvm <= vakajarjestaja.paattymis_pvm


def _compile_query(model, tilasto_pvm, additional_filter=Q()):
    filter_object = Q(alkamis_pvm__lte=tilasto_pvm) & (Q(paattymis_pvm__gte=tilasto_pvm) | Q(paattymis_pvm=None)) & additional_filter
    return model.objects.filter(filter_object).order_by('id').distinct('id')


def get_toimipaikat(vakajarjestaja, poiminta_pvm, tilasto_pvm, full_query, history_q):
    if history_q:
        filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm]
        with connection.cursor() as cursor:
            base_query = '''select distinct htp.id from
                            (select distinct on (id) * from varda_historicaltoimipaikka where history_date <= %s order by id, history_date desc) htp
                            where htp.history_type <> '-' and
                            htp.alkamis_pvm <= %s and (htp.paattymis_pvm >= %s or htp.paattymis_pvm is NULL)'''
            if not full_query:
                base_query += ' and htp.vakajarjestaja_id = %s'
                filters.append(vakajarjestaja.id)
            cursor.execute(base_query + ';', filters)
            row = cursor.fetchall()
            return row
    if full_query:
        return _compile_query(Toimipaikka, tilasto_pvm)
    return _compile_query(Toimipaikka, tilasto_pvm, Q(vakajarjestaja=vakajarjestaja))


def get_kielipainotukset(toimipaikat, poiminta_pvm, tilasto_pvm, history_q):
    if history_q:
        if not toimipaikat:
            return KieliPainotus.objects.none()
        filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm, tuple(toimipaikat)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hkp.id from varda_historicalkielipainotus hkp
                            join (select distinct on (id) id, history_id, history_type from varda_historicalkielipainotus
                            where history_date <= %s order by id, history_date desc) last_hkp
                            on hkp.history_id = last_hkp.history_id where last_hkp.history_type <> '-' and
                            hkp.alkamis_pvm <= %s and (hkp.paattymis_pvm >= %s or hkp.paattymis_pvm is NULL)
                            and hkp.toimipaikka_id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    return _compile_query(KieliPainotus, tilasto_pvm, Q(toimipaikka__in=toimipaikat))


def get_toiminnalliset_painotukset(toimipaikat, poiminta_pvm, tilasto_pvm, history_q):
    if history_q:
        if not toimipaikat:
            return ToiminnallinenPainotus.objects.none()
        filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm, tuple(toimipaikat)]
        with connection.cursor() as cursor:
            base_query = '''select distinct htp.id from varda_historicaltoiminnallinenpainotus htp
                            join (select distinct on (id) id, history_id, history_type from varda_historicaltoiminnallinenpainotus
                            where history_date <= %s order by id, history_date desc) last_htp
                            on htp.history_id = last_htp.history_id where last_htp.history_type <> '-' and
                            htp.alkamis_pvm <= %s and (htp.paattymis_pvm >= %s or htp.paattymis_pvm is NULL)
                            and htp.toimipaikka_id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    return _compile_query(ToiminnallinenPainotus, tilasto_pvm, Q(toimipaikka__in=toimipaikat))


def get_vakasuhteet(vakajarjestaja, poiminta_pvm, tilasto_pvm, full_query, history_q):
    if history_q:
        if not full_query and not vakajarjestaja:
            return Varhaiskasvatussuhde.objects.none()
        filters = [poiminta_pvm, poiminta_pvm, tilasto_pvm, tilasto_pvm]
        with connection.cursor() as cursor:
            base_query = '''select distinct hvs.id from varda_historicalvarhaiskasvatussuhde hvs
                            join varda_historicalvarhaiskasvatuspaatos hvap on hvap.id = hvs.varhaiskasvatuspaatos_id
                            join (select distinct on (id) * from varda_historicallapsi where history_date <= %s order by id, history_date desc) hl
                            on hl.id = hvap.lapsi_id
                            join (select distinct on (id) id, history_id, history_type from varda_historicalvarhaiskasvatussuhde
                            where history_date <= %s order by id, history_date desc) last_hvs
                            on hvs.history_id = last_hvs.history_id
                            where last_hvs.history_type <> '-' and
                            hvs.alkamis_pvm <= %s and (hvs.paattymis_pvm >= %s or hvs.paattymis_pvm is NULL)'''
            if not full_query:
                base_query += ' and (hl.vakatoimija_id = %s or hl.oma_organisaatio_id = %s or hl.paos_organisaatio_id = %s)'
                filters.extend([vakajarjestaja.id, vakajarjestaja.id, vakajarjestaja.id])
            cursor.execute(base_query + ';', filters)
            return cursor.fetchall()
    return _compile_query(Varhaiskasvatussuhde, tilasto_pvm, (Q(varhaiskasvatuspaatos__lapsi__vakatoimija=vakajarjestaja) |
                                                              Q(varhaiskasvatuspaatos__lapsi__oma_organisaatio=vakajarjestaja) |
                                                              Q(varhaiskasvatuspaatos__lapsi__paos_organisaatio=vakajarjestaja)))


def get_omat_vakasuhteet(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q):
    if history_q:
        if not vakasuhteet:
            return Varhaiskasvatussuhde.objects.none()
        filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm, tuple(vakasuhteet)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hvs.id from varda_historicalvarhaiskasvatussuhde hvs
                            join (select distinct on (id) id, history_id, history_type from varda_historicalvarhaiskasvatussuhde
                            where history_date <= %s order by id, history_date desc) last_hvs
                            on hvs.history_id = last_hvs.history_id
                            join varda_historicalvarhaiskasvatuspaatos hvp on hvp.id = hvs.varhaiskasvatuspaatos_id
                            where last_hvs.history_type <> '-' and lower(hvp.jarjestamismuoto_koodi) not in ('jm02', 'jm03') and
                            hvs.alkamis_pvm <= %s and (hvs.paattymis_pvm >= %s or hvs.paattymis_pvm is NULL)
                            and hvs.id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    return vakasuhteet.filter(~Q(varhaiskasvatuspaatos__jarjestamismuoto_koodi__iexact='jm02') &
                              ~Q(varhaiskasvatuspaatos__jarjestamismuoto_koodi__iexact='jm03'))


def get_paos_vakasuhteet(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q):
    if history_q:
        if not vakasuhteet:
            return Varhaiskasvatussuhde.objects.none()
        filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm, tuple(vakasuhteet)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hvs.id from varda_historicalvarhaiskasvatussuhde hvs
                            join (select distinct on (id) id, history_id, history_type from varda_historicalvarhaiskasvatussuhde
                            where history_date <= %s order by id, history_date desc) last_hvs
                            on hvs.history_id = last_hvs.history_id
                            join varda_historicalvarhaiskasvatuspaatos hvp on hvp.id = hvs.varhaiskasvatuspaatos_id
                            where last_hvs.history_type <> '-' and lower(hvp.jarjestamismuoto_koodi) in ('jm02', 'jm03') and
                            hvs.alkamis_pvm <= %s and (hvs.paattymis_pvm >= %s or hvs.paattymis_pvm is NULL)
                            and hvs.id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    return vakasuhteet.filter(Q(varhaiskasvatuspaatos__jarjestamismuoto_koodi__iexact='jm02') |
                              Q(varhaiskasvatuspaatos__jarjestamismuoto_koodi__iexact='jm03'))


def get_vakapaatokset(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q, additional_filter=Q()):
    if history_q:
        if not vakasuhteet:
            return Varhaiskasvatuspaatos.objects.none()
        filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm, tuple(vakasuhteet)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hvp.id from varda_historicalvarhaiskasvatuspaatos hvp
                            join (select distinct on (id) id, history_id, history_type from varda_historicalvarhaiskasvatuspaatos
                            where history_date <= %s order by id, history_date desc) last_hvp
                            on hvp.history_id = last_hvp.history_id
                            join varda_historicalvarhaiskasvatussuhde hvs on hvs.varhaiskasvatuspaatos_id = hvp.id
                            where last_hvp.history_type <> '-' and
                            hvp.alkamis_pvm <= %s and (hvp.paattymis_pvm >= %s or hvp.paattymis_pvm is NULL)
                            and hvs.id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    vakapaatos_id_list = vakasuhteet.values_list('varhaiskasvatuspaatos', flat=True)
    vakapaatos_filter = Q(id__in=vakapaatos_id_list)
    return _compile_query(Varhaiskasvatuspaatos, tilasto_pvm, Q(vakapaatos_filter, additional_filter))


def get_omat_vakapaatokset(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q, additional_filter=Q()):
    if history_q:
        if not vakasuhteet:
            return Varhaiskasvatuspaatos.objects.none()
        filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm, tuple(vakasuhteet)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hvp.id from varda_historicalvarhaiskasvatuspaatos hvp
                            join (select distinct on (id) id, history_id, history_type from varda_historicalvarhaiskasvatuspaatos
                            where history_date <= %s order by id, history_date desc) last_hvp
                            on hvp.history_id = last_hvp.history_id
                            join varda_historicalvarhaiskasvatussuhde hvs on hvs.varhaiskasvatuspaatos_id = hvp.id
                            where last_hvp.history_type <> '-' and lower(hvp.jarjestamismuoto_koodi) not in ('jm02', 'jm03')
                            and hvp.alkamis_pvm <= %s and (hvp.paattymis_pvm >= %s or hvp.paattymis_pvm is NULL)
                            and hvs.id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    additional_filter = additional_filter & (~Q(jarjestamismuoto_koodi__iexact='jm02') |
                                             ~Q(jarjestamismuoto_koodi__iexact='jm03'))
    return get_vakapaatokset(vakasuhteet, None, tilasto_pvm, history_q, additional_filter)


def get_paos_vakapaatokset(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q, additional_filter=Q()):
    if history_q:
        if not vakasuhteet:
            return Varhaiskasvatuspaatos.objects.none()
        filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm, tuple(vakasuhteet)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hvp.id from varda_historicalvarhaiskasvatuspaatos hvp
                            join (select distinct on (id) id, history_id, history_type from varda_historicalvarhaiskasvatuspaatos
                            where history_date <= %s order by id, history_date desc) last_hvp
                            on hvp.history_id = last_hvp.history_id
                            join varda_historicalvarhaiskasvatussuhde hvs on hvs.varhaiskasvatuspaatos_id = hvp.id
                            where last_hvp.history_type <> '-' and lower(hvp.jarjestamismuoto_koodi) in ('jm02', 'jm03')
                            and hvp.alkamis_pvm <= %s and (hvp.paattymis_pvm >= %s or hvp.paattymis_pvm is NULL)
                            and hvs.id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    additional_filter = additional_filter & (Q(jarjestamismuoto_koodi__iexact='jm02') |
                                             Q(jarjestamismuoto_koodi__iexact='jm03'))
    return get_vakapaatokset(vakasuhteet, None, tilasto_pvm, history_q, additional_filter)


def get_vuorohoito_vakapaatokset(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q):
    if history_q:
        if not vakasuhteet:
            return Varhaiskasvatuspaatos.objects.none()
        filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm, tuple(vakasuhteet)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hvp.id from varda_historicalvarhaiskasvatuspaatos hvp
                            join (select distinct on (id) id, history_id, history_type from varda_historicalvarhaiskasvatuspaatos
                            where history_date <= %s order by id, history_date desc) last_hvp
                            on hvp.history_id = last_hvp.history_id
                            join varda_historicalvarhaiskasvatussuhde hvs on hvs.varhaiskasvatuspaatos_id = hvp.id
                            where last_hvp.history_type <> '-' and hvp.vuorohoito_kytkin = 'true' and
                            hvp.alkamis_pvm <= %s and (hvp.paattymis_pvm >= %s or hvp.paattymis_pvm is NULL)
                            and hvs.id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    additional_filter = Q(vuorohoito_kytkin=True)
    return get_vakapaatokset(vakasuhteet, None, tilasto_pvm, history_q, additional_filter)


def get_omat_vuorohoito_vakapaatokset(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q):
    if history_q:
        if not vakasuhteet:
            return Varhaiskasvatuspaatos.objects.none()
        filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm, tuple(vakasuhteet)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hvp.id from varda_historicalvarhaiskasvatuspaatos hvp
                            join (select distinct on (id) id, history_id, history_type from varda_historicalvarhaiskasvatuspaatos
                            where history_date <= %s order by id, history_date desc) last_hvp
                            on hvp.history_id = last_hvp.history_id
                            join varda_historicalvarhaiskasvatussuhde hvs on hvs.varhaiskasvatuspaatos_id = hvp.id
                            where last_hvp.history_type <> '-' and lower(hvp.jarjestamismuoto_koodi) not in ('jm02', 'jm03')
                            and hvp.vuorohoito_kytkin = 'true' and hvp.alkamis_pvm <= %s and
                            (hvp.paattymis_pvm >= %s or hvp.paattymis_pvm is NULL) and hvs.id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    additional_filter = Q(vuorohoito_kytkin=True)
    return get_omat_vakapaatokset(vakasuhteet, None, tilasto_pvm, history_q, additional_filter)


def get_paos_vuorohoito_vakapaatokset(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q):
    if history_q:
        if not vakasuhteet:
            return Varhaiskasvatuspaatos.objects.none()
        filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm, tuple(vakasuhteet)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hvp.id from varda_historicalvarhaiskasvatuspaatos hvp
                            join (select distinct on (id) id, history_id, history_type from varda_historicalvarhaiskasvatuspaatos
                            where history_date <= %s order by id, history_date desc) last_hvp on hvp.history_id = last_hvp.history_id
                            join varda_historicalvarhaiskasvatussuhde hvs on hvs.varhaiskasvatuspaatos_id = hvp.id
                            where last_hvp.history_type <> '-' and lower(hvp.jarjestamismuoto_koodi) in ('jm02', 'jm03')
                            and hvp.vuorohoito_kytkin = 'true' and hvp.alkamis_pvm <= %s and
                            (hvp.paattymis_pvm >= %s or hvp.paattymis_pvm is NULL) and hvs.id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    additional_filter = Q(vuorohoito_kytkin=True)
    return get_paos_vakapaatokset(vakasuhteet, None, tilasto_pvm, history_q, additional_filter)


def get_lapset(vakapaatokset, poiminta_pvm, additional_filter, history_q):
    if history_q:
        if not vakapaatokset:
            return Lapsi.objects.none()
        filters = [poiminta_pvm, tuple(vakapaatokset)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hl.id from varda_historicallapsi hl
                            join (select distinct on (id) id, history_id, history_type from varda_historicallapsi
                            where history_date <= %s order by id, history_date desc) last_hl
                            on hl.history_id = last_hl.history_id
                            join varda_historicalvarhaiskasvatuspaatos hvp on hvp.lapsi_id = hl.id
                            where last_hl.history_type <> '-' and hvp.id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    lapsi_id_list = vakapaatokset.filter(additional_filter).values_list('lapsi', flat=True)
    return Lapsi.objects.filter(id__in=lapsi_id_list)


def get_omat_lapset(vakajarjestaja, vakapaatokset, poiminta_pvm, full_query, history_q):
    if history_q:
        if not vakapaatokset:
            return Lapsi.objects.none()
        filters = [poiminta_pvm, tuple(vakapaatokset)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hl.id from varda_historicallapsi hl
                            join (select distinct on (id) id, history_id, history_type from varda_historicallapsi
                            where history_date <= %s order by id, history_date desc) last_hl
                            on hl.history_id = last_hl.history_id
                            join varda_historicalvarhaiskasvatuspaatos hvp on hvp.lapsi_id = hl.id
                            where last_hl.history_type <> '-' and hvp.id in %s'''
            if full_query:
                base_query += ' and hl.vakatoimija_id is not Null;'
            else:
                base_query += ' and hl.vakatoimija_id = %s;'
                filters.append(vakajarjestaja.id)
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    additional_filter = Q(lapsi__vakatoimija=vakajarjestaja)
    return get_lapset(vakapaatokset, poiminta_pvm, additional_filter, history_q)


def get_paos_lapset(vakajarjestaja, vakapaatokset, poiminta_pvm, full_query, history_q):
    if history_q:
        if not vakapaatokset:
            return Lapsi.objects.none()
        filters = [poiminta_pvm, tuple(vakapaatokset)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hl.id from varda_historicallapsi hl
                            join (select distinct on (id) id, history_id, history_type from varda_historicallapsi
                            where history_date <= %s order by id, history_date desc) last_hl
                            on hl.history_id = last_hl.history_id
                            join varda_historicalvarhaiskasvatuspaatos hvp on hvp.lapsi_id = hl.id
                            where last_hl.history_type <> '-' and hvp.id in %s'''
            if full_query:
                base_query += ' and hl.oma_organisaatio_id is not Null;'
            else:
                base_query += ' and (hl.oma_organisaatio_id = %s or hl.paos_organisaatio_id = %s);'
                filters.extend([vakajarjestaja.id, vakajarjestaja.id])
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    additional_filter = Q(lapsi__oma_organisaatio=vakajarjestaja) | Q(lapsi__paos_organisaatio=vakajarjestaja)
    return get_lapset(vakapaatokset, poiminta_pvm, additional_filter, history_q)


def get_henkilot(lapset, poiminta_pvm, history_q):
    if history_q:
        if not lapset:
            return Henkilo.objects.none()
        filters = [poiminta_pvm, tuple(lapset)]
        with connection.cursor() as cursor:
            base_query = '''select distinct hh.id from varda_historicalhenkilo hh
                            join (select distinct on (id) id, history_id, history_type from varda_historicalhenkilo
                            where history_date <= %s order by id, history_date desc) last_hh
                            on hh.history_id = last_hh.history_id
                            join varda_historicallapsi hl on hl.henkilo_id = hh.id
                            where last_hh.history_type <> '-' and hl.id in %s;'''
            cursor.execute(base_query, filters)
            return cursor.fetchall()
    henkilo_id_list = lapset.values_list('henkilo', flat=True)
    return Henkilo.objects.filter(id__in=henkilo_id_list)


def get_maksutiedot(vakajarjestaja, full_query, poiminta_pvm, reporting_date, paos_kytkin, maksun_peruste):
    # historical paos lapsi has both paos_kytkin = false and paos_kytkin = true rows on history table so paos_kytkin
    # cannot be used directly
    filters = [poiminta_pvm, poiminta_pvm, reporting_date, reporting_date]
    with connection.cursor() as cursor:
        base_query = '''
                select count(distinct(hmt.id)) from varda_historicalmaksutieto hmt
                join varda_historicalmaksutietohuoltajuussuhde hmths on hmths.maksutieto_id = hmt.id
                join varda_historicalhuoltajuussuhde hhs on hhs.id = hmths.huoltajuussuhde_id
                join (select distinct on (id) * from varda_historicallapsi where history_date <= %s order by id, history_date desc) hl on hl.id = hhs.lapsi_id
                join (select distinct on (id) id, history_id, history_type from varda_historicalmaksutieto
                             where history_date <= %s order by id, history_date desc) last_hmt
                on hmt.history_id = last_hmt.history_id
                where hmt.alkamis_pvm <= %s and (hmt.paattymis_pvm >= %s or
                hmt.paattymis_pvm is NULL) and last_hmt.history_type <> '-'
                '''
        if maksun_peruste:
            base_query += ' and UPPER(maksun_peruste_koodi) = %s'
            filters.append(maksun_peruste)
        if not full_query:
            if paos_kytkin is None:
                base_query += ' and (hl.vakatoimija_id = %s or hl.oma_organisaatio_id = %s or hl.paos_organisaatio_id = %s)'
                filters.extend([vakajarjestaja.id, vakajarjestaja.id, vakajarjestaja.id])
            elif not paos_kytkin:
                base_query += ' and hl.vakatoimija_id = %s'
                filters.append(vakajarjestaja.id)
            elif paos_kytkin:
                base_query += ' and (hl.oma_organisaatio_id = %s or hl.paos_organisaatio_id = %s)'
                filters.extend([vakajarjestaja.id, vakajarjestaja.id])
        else:
            if paos_kytkin is not None and not paos_kytkin:
                base_query += ' and hl.vakatoimija_id is not NULL'
            elif paos_kytkin:
                base_query += ' and hl.oma_organisaatio_id is not NULL'
        cursor.execute(base_query + ';', filters)
        row = cursor.fetchone()
        return row[0]


def get_top_results(request, queryset, permission_group_list, oid_list):
    """
    Function that returns limited amount of results from a queryset based on user permissions. Used for x_top fields.
    :param request: request object
    :param queryset: base queryset
    :param permission_group_list: List of accepted permission groups (Z4_CasKayttoOikeudet values)
    :param oid_list: list of accepted OIDs (e.g. Organisaatio, Toimipaikka)
    :return: List of object URIs
    """
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
