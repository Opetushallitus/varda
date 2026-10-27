import logging

from contextlib import contextmanager

from django.db import DEFAULT_DB_ALIAS, connections, transaction
from django.db.models import Prefetch, Q

from varda.constants import TYOSUHDE_KOODI_MAARAAIKAINEN
from varda.enums.koodistot import Koodistot
from varda.enums.translation import Translation as T
from varda.excel_export.base import BaseExcelReportGenerator
from varda.excel_export.constants import ExcelReportType
from varda.excel_export.utils import _get_code_translation, _get_json_code_translation
from varda.misc import decrypt_henkilotunnus
from varda.misc_queries import get_active_filter, get_active_on_any_date_filter
from varda.models import Palvelussuhde, PidempiPoissaolo, Tutkinto, Tyoskentelypaikka

logger = logging.getLogger(__name__)

TYONTEKIJA_HEADERS = (
    T.EXCEL_OPPIJANUMERO,
    T.EXCEL_ETUNIMET,
    T.EXCEL_SUKUNIMI,
    T.EXCEL_HETU,
    T.EXCEL_EMAIL,
    T.EXCEL_TURVAKIELTO,
    T.EXCEL_TYONTEKIJA_ID,
    T.EXCEL_LAHDEJARJESTELMA,
    T.EXCEL_PALVELUSSUHDE_ID,
    T.EXCEL_PALVELUSSUHDE_TUNNISTE,
    T.EXCEL_PALVELUSSUHDE_TYYPPI,
    T.EXCEL_TYOAIKA,
    T.EXCEL_TUTKINTO,
    T.EXCEL_TYOAIKA_VIIKOSSA,
    T.EXCEL_ALKAMIS_PVM,
    T.EXCEL_PAATTYMIS_PVM,
    T.EXCEL_TYOSKENTELYPAIKKA_ID,
    T.EXCEL_TYOSKENTELYPAIKKA_TUNNISTE,
    T.EXCEL_KIERTAVA_KYTKIN,
    T.EXCEL_TOIMIPAIKKA_NIMI,
    T.EXCEL_TOIMIPAIKKA_OID,
    T.EXCEL_TOIMIPAIKKA_ID,
    T.EXCEL_TEHTAVANIMIKE,
    T.EXCEL_KELPOISUUS_KYTKIN,
    T.EXCEL_ALKAMIS_PVM,
    T.EXCEL_PAATTYMIS_PVM,
    T.EXCEL_PIDEMPI_POISSAOLO_ID,
    T.EXCEL_PIDEMPI_POISSAOLO_TUNNISTE,
    T.EXCEL_ALKAMIS_PVM,
    T.EXCEL_PAATTYMIS_PVM,
)


class TyontekijatiedotReportGeneratorBase(BaseExcelReportGenerator):
    def __init__(self, report, data_db_alias=DEFAULT_DB_ALIAS, report_data=None):
        super().__init__(report, data_db_alias=data_db_alias)
        self.report_data = report_data

    def _get_palvelussuhde_filter(self):
        raise NotImplementedError

    def _get_tyontekijatiedot_queryset(self, palvelussuhde_filter=Q()):
        vakajarjestaja_filter = Q(tyontekija__vakajarjestaja=self.organisaatio_id)
        if self.toimipaikka_id:
            vakajarjestaja_filter &= Q(tyoskentelypaikat__toimipaikka=self.toimipaikka_id)

        tyoskentelypaikka_queryset = (
            Tyoskentelypaikka.objects.using(self.data_db_alias).select_related("toimipaikka").order_by("alkamis_pvm")
        )
        if self.toimipaikka_id:
            tyoskentelypaikka_queryset = tyoskentelypaikka_queryset.filter(toimipaikka=self.toimipaikka_id)
        poissaolo_queryset = PidempiPoissaolo.objects.using(self.data_db_alias).order_by("alkamis_pvm")
        tutkinto_queryset = Tutkinto.objects.using(self.data_db_alias)

        return (
            Palvelussuhde.objects.using(self.data_db_alias)
            .filter(vakajarjestaja_filter & palvelussuhde_filter)
            .distinct()
            .select_related("tyontekija__henkilo")
            .prefetch_related(
                Prefetch(
                    "tyoskentelypaikat",
                    queryset=tyoskentelypaikka_queryset,
                    to_attr="_report_tyoskentelypaikat",
                ),
                Prefetch(
                    "pidemmatpoissaolot",
                    queryset=poissaolo_queryset,
                    to_attr="_report_pidemmatpoissaolot",
                ),
                Prefetch(
                    "tyontekija__henkilo__tutkinnot",
                    queryset=tutkinto_queryset,
                ),
            )
            .order_by("tyontekija__henkilo__sukunimi", "tyontekija__henkilo__etunimet", "alkamis_pvm")
        )

    def _create_excel_report(self):
        if self.report_data is not None:
            return self._create_excel_report_from_data(self.report_data)
        palvelussuhde_qs = self._get_tyontekijatiedot_queryset(self._get_palvelussuhde_filter())

        tutkinto_codes = self._get_koodisto_with_translations(Koodistot.tutkinto_koodit.value)
        tyosuhde_codes = self._get_koodisto_with_translations(Koodistot.tyosuhde_koodit.value)
        tyoaika_codes = self._get_koodisto_with_translations(Koodistot.tyoaika_koodit.value)
        tehtavanimike_codes = self._get_koodisto_with_translations(Koodistot.tehtavanimike_koodit.value)
        lahdejarjestelma_codes = self._get_koodisto_with_translations(Koodistot.lahdejarjestelma_koodit.value)

        tyontekija_sheet = self._add_worksheet(T.EXCEL_TYONTEKIJATIEDOT)
        self._write_headers(tyontekija_sheet, TYONTEKIJA_HEADERS)

        index = 1
        for palvelussuhde in palvelussuhde_qs.iterator(chunk_size=500):
            tyoskentelypaikka_qs = palvelussuhde._report_tyoskentelypaikat
            poissaolo_qs = palvelussuhde._report_pidemmatpoissaolot
            tyontekija = palvelussuhde.tyontekija
            henkilo = tyontekija.henkilo
            for type_index, data_set in enumerate(
                (
                    tyoskentelypaikka_qs,
                    poissaolo_qs,
                )
            ):
                for data_instance in data_set:
                    # Tyontekija information
                    tyontekija_values = [
                        henkilo.henkilo_oid,
                        henkilo.etunimet,
                        henkilo.sukunimi,
                        decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id, raise_error=False),
                        tyontekija.sahkopostiosoite,
                        self._get_boolean_translation(henkilo.turvakielto),
                        tyontekija.id,
                        _get_code_translation(lahdejarjestelma_codes, tyontekija.lahdejarjestelma),
                    ]

                    # Palvelussuhde information

                    # We use newest Tutkinto/tutkinto_koodi instead of tutkinto_koodi
                    # in Palvelussuhde. (Palvelussuhde/tutkinto_koodi is used as backup)

                    # Filter the prefetched tutkinnot to get latest Tutkinto with the correct vakajarjestaja_id
                    filtered_tutkinnot = [
                        tutkinto
                        for tutkinto in palvelussuhde.tyontekija.henkilo.tutkinnot.all()
                        if tutkinto.vakajarjestaja_id == self.organisaatio_id
                    ]
                    latest_tutkinto = max(filtered_tutkinnot, key=lambda t: t.luonti_pvm, default=None)
                    latest_tutkinto_koodi = latest_tutkinto.tutkinto_koodi if latest_tutkinto else None

                    tyontekija_values.extend(
                        [
                            palvelussuhde.id,
                            palvelussuhde.tunniste,
                            _get_code_translation(tyosuhde_codes, palvelussuhde.tyosuhde_koodi),
                            _get_code_translation(tyoaika_codes, palvelussuhde.tyoaika_koodi),
                            _get_code_translation(tutkinto_codes, latest_tutkinto_koodi),
                            palvelussuhde.tyoaika_viikossa,
                            palvelussuhde.alkamis_pvm,
                            palvelussuhde.paattymis_pvm,
                        ]
                    )

                    if type_index == 0:
                        # Tyoskentelypaikka
                        tyontekija_values.extend(
                            [
                                data_instance.id,
                                data_instance.tunniste,
                                self._get_boolean_translation(data_instance.kiertava_tyontekija_kytkin),
                            ]
                        )
                        if data_instance.toimipaikka:
                            tyontekija_values.extend(
                                [
                                    data_instance.toimipaikka.nimi,
                                    data_instance.toimipaikka.organisaatio_oid,
                                    data_instance.toimipaikka.id,
                                ]
                            )
                        else:
                            tyontekija_values.extend([None, None, None])
                        tyontekija_values.extend(
                            [
                                _get_code_translation(tehtavanimike_codes, data_instance.tehtavanimike_koodi),
                                self._get_boolean_translation(data_instance.kelpoisuus_kytkin),
                                data_instance.alkamis_pvm,
                                data_instance.paattymis_pvm,
                            ]
                        )
                    else:
                        # Pidempi poissaolo
                        # Because every row has Tyoskentelypaikka and Pidempi Poissaolo columns, fill Tyoskentelypaikka
                        # columns with None
                        tyontekija_values.extend([None] * 10)
                        tyontekija_values.extend(
                            [data_instance.id, data_instance.tunniste, data_instance.alkamis_pvm, data_instance.paattymis_pvm]
                        )

                    self.henkilo_id_oid_set.add(
                        (
                            henkilo.id,
                            henkilo.henkilo_oid,
                        )
                    )
                    self._write_row(tyontekija_sheet, index, tyontekija_values)
                    index += 1

    def _create_excel_report_from_data(self, report_data):
        self.henkilo_id_oid_set.update(report_data["henkilo_id_oid_set"])
        tutkinto_koodisto = report_data["koodistot"][Koodistot.tutkinto_koodit.value]
        tyosuhde_koodisto = report_data["koodistot"][Koodistot.tyosuhde_koodit.value]
        tyoaika_koodisto = report_data["koodistot"][Koodistot.tyoaika_koodit.value]
        tehtavanimike_koodisto = report_data["koodistot"][Koodistot.tehtavanimike_koodit.value]
        lahdejarjestelma_koodisto = report_data["koodistot"][Koodistot.lahdejarjestelma_koodit.value]

        tyontekija_sheet = self._add_worksheet(T.EXCEL_TYONTEKIJATIEDOT)
        self._write_headers(tyontekija_sheet, TYONTEKIJA_HEADERS)
        index = 1
        for tyontekija_data in report_data["tyontekijat"]:
            for palvelussuhde in tyontekija_data["palvelussuhteet"]:
                rows = [(tyoskentelypaikka, 0) for tyoskentelypaikka in palvelussuhde["tyoskentelypaikat"]]
                rows.extend((poissaolo, 1) for poissaolo in palvelussuhde["poissaolot"])
                for data_instance, type_index in rows:
                    henkilo = tyontekija_data["henkilo"]
                    tyontekija = tyontekija_data["tyontekija"]
                    tyontekija_values = [
                        henkilo["henkilo_oid"],
                        henkilo["etunimet"],
                        henkilo["sukunimi"],
                        henkilo["hetu"],
                        tyontekija["sahkopostiosoite"],
                        self._get_boolean_translation(henkilo["turvakielto"]),
                        tyontekija["id"],
                        _get_code_translation(lahdejarjestelma_koodisto, tyontekija["lahdejarjestelma"]),
                        palvelussuhde["id"],
                        palvelussuhde["tunniste"],
                        _get_code_translation(tyosuhde_koodisto, palvelussuhde["tyosuhde_koodi"]),
                        _get_code_translation(tyoaika_koodisto, palvelussuhde["tyoaika_koodi"]),
                        _get_code_translation(tutkinto_koodisto, palvelussuhde["tutkinto_koodi"]),
                        palvelussuhde["tyoaika_viikossa"],
                        palvelussuhde["alkamis_pvm"],
                        palvelussuhde["paattymis_pvm"],
                    ]
                    if type_index == 0:
                        toimipaikka = data_instance["toimipaikka"]
                        tyontekija_values.extend(
                            [
                                data_instance["id"],
                                data_instance["tunniste"],
                                self._get_boolean_translation(data_instance["kiertava"]),
                                toimipaikka["nimi"] if toimipaikka else None,
                                toimipaikka["oid"] if toimipaikka else None,
                                toimipaikka["id"] if toimipaikka else None,
                                _get_code_translation(tehtavanimike_koodisto, data_instance["tehtavanimike_koodi"]),
                                self._get_boolean_translation(data_instance["kelpoisuus"]),
                                data_instance["alkamis_pvm"],
                                data_instance["paattymis_pvm"],
                            ]
                        )
                    else:
                        tyontekija_values.extend([None] * 10)
                        tyontekija_values.extend(
                            [
                                data_instance["id"],
                                data_instance["tunniste"],
                                data_instance["alkamis_pvm"],
                                data_instance["paattymis_pvm"],
                            ]
                        )
                    self._write_row(tyontekija_sheet, index, tyontekija_values)
                    index += 1


class TyontekijatiedotVoimassaReportGenerator(TyontekijatiedotReportGeneratorBase):
    """
    report_data can be given when the data has already been loaded with load_tyontekijatiedot_data
    (mass reports), so that Excel and JSON are created from the same snapshot.
    """

    filename_key = T.EXCEL_FILENAME_TYONTEKIJATIEDOT_VOIMASSA

    def _get_palvelussuhde_filter(self):
        target_date = self._target_date()
        return get_active_filter(target_date) & get_active_filter(target_date, prefix="tyoskentelypaikat")


class TyontekijatiedotMaaraaikaisetVoimassaReportGenerator(TyontekijatiedotReportGeneratorBase):
    filename_key = T.EXCEL_FILENAME_TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA

    def _get_palvelussuhde_filter(self):
        target_date = self._target_date()
        target_date_secondary = self.report.target_date_secondary or target_date
        return (
            get_active_on_any_date_filter(target_date, target_date_secondary)
            & get_active_on_any_date_filter(target_date, target_date_secondary, prefix="tyoskentelypaikat")
            & Q(tyosuhde_koodi=TYOSUHDE_KOODI_MAARAAIKAINEN)
        )


@contextmanager
def _massahaku_snapshot(data_db_alias):
    if data_db_alias not in connections.databases:
        logger.warning(
            "Skipping repeatable-read snapshot for massahaku reports: database alias %s is not configured",
            data_db_alias,
        )
        yield
        return

    if connections[data_db_alias].in_atomic_block:
        logger.warning(
            "Skipping repeatable-read snapshot for massahaku reports: database alias %s is already in an atomic block",
            data_db_alias,
        )
        yield
        return

    with transaction.atomic(using=data_db_alias):
        with connections[data_db_alias].cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        yield


def _json_date(value):
    return value.isoformat() if value else None


def load_tyontekijatiedot_data(generator, palvelussuhde_filter):
    palvelussuhde_qs = generator._get_tyontekijatiedot_queryset(palvelussuhde_filter)

    koodistot = {
        koodisto: generator._get_koodisto_with_translations(koodisto)
        for koodisto in (
            Koodistot.tutkinto_koodit.value,
            Koodistot.tyosuhde_koodit.value,
            Koodistot.tyoaika_koodit.value,
            Koodistot.tehtavanimike_koodit.value,
            Koodistot.lahdejarjestelma_koodit.value,
        )
    }

    tyontekijat = {}
    henkilo_id_oid_set = set()
    for palvelussuhde in palvelussuhde_qs.iterator(chunk_size=500):
        tyontekija = palvelussuhde.tyontekija
        henkilo = tyontekija.henkilo
        henkilo_id_oid_set.add((henkilo.id, henkilo.henkilo_oid))
        tyontekija_data = tyontekijat.setdefault(
            tyontekija.id,
            {
                "henkilo": {
                    "henkilo_oid": henkilo.henkilo_oid,
                    "etunimet": henkilo.etunimet or None,
                    "sukunimi": henkilo.sukunimi or None,
                    "hetu": decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id, raise_error=False) or None,
                    "turvakielto": bool(henkilo.turvakielto),
                },
                "tyontekija": {
                    "id": tyontekija.id,
                    "sahkopostiosoite": tyontekija.sahkopostiosoite or None,
                    "lahdejarjestelma": tyontekija.lahdejarjestelma,
                },
                "palvelussuhteet": [],
            },
        )
        palvelussuhde_data = {
            "id": palvelussuhde.id,
            "tunniste": palvelussuhde.tunniste or None,
            "tyosuhde_koodi": palvelussuhde.tyosuhde_koodi,
            "tyoaika_koodi": palvelussuhde.tyoaika_koodi,
            "tutkinto_koodi": None,
            "tyoaika_viikossa": float(palvelussuhde.tyoaika_viikossa) if palvelussuhde.tyoaika_viikossa is not None else None,
            "alkamis_pvm": palvelussuhde.alkamis_pvm,
            "paattymis_pvm": palvelussuhde.paattymis_pvm,
            "tyoskentelypaikat": [],
            "poissaolot": [],
        }
        filtered_tutkinnot = [
            tutkinto for tutkinto in henkilo.tutkinnot.all() if tutkinto.vakajarjestaja_id == generator.organisaatio_id
        ]
        latest_tutkinto = max(filtered_tutkinnot, key=lambda tutkinto: tutkinto.luonti_pvm, default=None)
        if latest_tutkinto:
            palvelussuhde_data["tutkinto_koodi"] = latest_tutkinto.tutkinto_koodi

        tyontekija_data["palvelussuhteet"].append(palvelussuhde_data)

        tyoskentelypaikat = palvelussuhde._report_tyoskentelypaikat
        for tyoskentelypaikka in tyoskentelypaikat:
            toimipaikka = tyoskentelypaikka.toimipaikka
            palvelussuhde_data["tyoskentelypaikat"].append(
                {
                    "id": tyoskentelypaikka.id,
                    "tunniste": tyoskentelypaikka.tunniste or None,
                    "kiertava": bool(tyoskentelypaikka.kiertava_tyontekija_kytkin),
                    "toimipaikka": (
                        {
                            "nimi": toimipaikka.nimi,
                            "oid": toimipaikka.organisaatio_oid,
                            "id": toimipaikka.id,
                        }
                        if toimipaikka
                        else None
                    ),
                    "tehtavanimike_koodi": tyoskentelypaikka.tehtavanimike_koodi,
                    "kelpoisuus": bool(tyoskentelypaikka.kelpoisuus_kytkin),
                    "alkamis_pvm": tyoskentelypaikka.alkamis_pvm,
                    "paattymis_pvm": tyoskentelypaikka.paattymis_pvm,
                }
            )
        poissaolot = palvelussuhde._report_pidemmatpoissaolot
        for poissaolo in poissaolot:
            palvelussuhde_data["poissaolot"].append(
                {
                    "id": poissaolo.id,
                    "tunniste": poissaolo.tunniste or None,
                    "alkamis_pvm": poissaolo.alkamis_pvm,
                    "paattymis_pvm": poissaolo.paattymis_pvm,
                }
            )

    return {
        "tyontekijat": list(tyontekijat.values()),
        "koodistot": koodistot,
        "henkilo_id_oid_set": henkilo_id_oid_set,
    }


def create_tyontekijatiedot_json_from_data(report_data, report_type):
    koodistot = report_data["koodistot"]
    tutkinto_koodisto = koodistot[Koodistot.tutkinto_koodit.value]
    tyosuhde_koodisto = koodistot[Koodistot.tyosuhde_koodit.value]
    tyoaika_koodisto = koodistot[Koodistot.tyoaika_koodit.value]
    tehtavanimike_koodisto = koodistot[Koodistot.tehtavanimike_koodit.value]
    lahdejarjestelma_koodisto = koodistot[Koodistot.lahdejarjestelma_koodit.value]
    tyontekijat = []
    for source_tyontekija in report_data["tyontekijat"]:
        henkilo = source_tyontekija["henkilo"]
        tyontekija_data = source_tyontekija["tyontekija"]
        tyontekija = {
            "oppijanumero": henkilo["henkilo_oid"],
            "etunimet": henkilo["etunimet"],
            "sukunimi": henkilo["sukunimi"],
            "hetu": henkilo["hetu"],
            "sahkopostiosoite": tyontekija_data["sahkopostiosoite"],
            "turvakielto": henkilo["turvakielto"],
            "tyontekija_id": tyontekija_data["id"],
            "lahdejarjestelma": _get_json_code_translation(lahdejarjestelma_koodisto, tyontekija_data["lahdejarjestelma"]),
            "palvelussuhteet": [],
        }
        for source_palvelussuhde in source_tyontekija["palvelussuhteet"]:
            palvelussuhde = {
                "id": source_palvelussuhde["id"],
                "tunniste": source_palvelussuhde["tunniste"],
                "palvelussuhteen_tyyppi": _get_json_code_translation(tyosuhde_koodisto, source_palvelussuhde["tyosuhde_koodi"]),
                "tyoajan_tyyppi": _get_json_code_translation(tyoaika_koodisto, source_palvelussuhde["tyoaika_koodi"]),
                "tutkinto": _get_json_code_translation(tutkinto_koodisto, source_palvelussuhde["tutkinto_koodi"]),
                "viikkotyoaika": source_palvelussuhde["tyoaika_viikossa"],
                "alkamis_pvm": _json_date(source_palvelussuhde["alkamis_pvm"]),
                "paattymis_pvm": _json_date(source_palvelussuhde["paattymis_pvm"]),
                "tyoskentelypaikat": [],
                "poissaolot": [],
            }
            for source_tyoskentelypaikka in source_palvelussuhde["tyoskentelypaikat"]:
                palvelussuhde["tyoskentelypaikat"].append(
                    {
                        "id": source_tyoskentelypaikka["id"],
                        "tunniste": source_tyoskentelypaikka["tunniste"],
                        "kiertava": source_tyoskentelypaikka["kiertava"],
                        "toimipaikka": source_tyoskentelypaikka["toimipaikka"],
                        "tehtavanimike": _get_json_code_translation(
                            tehtavanimike_koodisto, source_tyoskentelypaikka["tehtavanimike_koodi"]
                        ),
                        "kelpoisuus": source_tyoskentelypaikka["kelpoisuus"],
                        "alkamis_pvm": _json_date(source_tyoskentelypaikka["alkamis_pvm"]),
                        "paattymis_pvm": _json_date(source_tyoskentelypaikka["paattymis_pvm"]),
                    }
                )
            for source_poissaolo in source_palvelussuhde["poissaolot"]:
                palvelussuhde["poissaolot"].append(
                    {
                        "id": source_poissaolo["id"],
                        "tunniste": source_poissaolo["tunniste"],
                        "alkamis_pvm": _json_date(source_poissaolo["alkamis_pvm"]),
                        "paattymis_pvm": _json_date(source_poissaolo["paattymis_pvm"]),
                    }
                )
            tyontekija["palvelussuhteet"].append(palvelussuhde)
        tyontekijat.append(tyontekija)
    return {
        "raportti": report_type,
        "schema_version": 1,
        "tyontekijat": tyontekijat,
    }


def create_tyontekijatiedot_voimassa_json_from_data(report_data):
    return create_tyontekijatiedot_json_from_data(report_data, ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value)
