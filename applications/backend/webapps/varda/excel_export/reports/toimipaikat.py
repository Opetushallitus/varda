from django.db import DEFAULT_DB_ALIAS
from django.db.models import Q

from varda.enums.koodistot import Koodistot
from varda.enums.translation import Translation as T
from varda.excel_export.base import BaseExcelReportGenerator
from varda.excel_export.constants import ExcelReportType
from varda.excel_export.utils import _get_code_translation, _get_json_code_translation, _get_multiple_code_translations
from varda.misc import TemporaryObject
from varda.misc_queries import get_active_filter
from varda.models import Toimipaikka

TOIMIPAIKKA_HEADERS = (
    T.EXCEL_NIMI,
    T.EXCEL_OID,
    T.EXCEL_ID,
    T.EXCEL_LAHDEJARJESTELMA,
    T.EXCEL_TUNNISTE,
    T.EXCEL_PALVELUNTUOTTAJA_NIMI,
    T.EXCEL_PALVELUNTUOTTAJA_OID,
    T.EXCEL_ALKAMIS_PVM,
    T.EXCEL_PAATTYMIS_PVM,
    T.EXCEL_KASVATUSOPILLINEN_JARJESTELMA,
    T.EXCEL_TOIMINTAMUOTO,
    T.EXCEL_TOIMINTAKIELI,
    T.EXCEL_JARJESTAMISMUOTO,
    T.EXCEL_VARHAISKASVATUSPAIKAT,
    T.EXCEL_KUNTA,
    T.EXCEL_KAYNTIOSOITE,
    T.EXCEL_POSTINUMERO,
    T.EXCEL_POSTITOIMIPAIKKA,
    T.EXCEL_POSTIOSOITE,
    T.EXCEL_POSTINUMERO,
    T.EXCEL_POSTITOIMIPAIKKA,
    T.EXCEL_PUHELINNUMERO,
    T.EXCEL_EMAIL,
    T.EXCEL_PAINOTUS_ID,
    T.EXCEL_LAHDEJARJESTELMA,
    T.EXCEL_TUNNISTE,
    T.EXCEL_TOIMINNALLINEN_PAINOTUS,
    T.EXCEL_KIELIPAINOTUS,
    T.EXCEL_KIELIPAINOTUS_TYYPPI,
    T.EXCEL_ALKAMIS_PVM,
    T.EXCEL_PAATTYMIS_PVM,
)


class ToimipaikatVoimassaReportGenerator(BaseExcelReportGenerator):
    filename_key = T.EXCEL_FILENAME_TOIMIPAIKAT_VOIMASSA

    def __init__(self, report, data_db_alias=DEFAULT_DB_ALIAS, report_data=None):
        super().__init__(report, data_db_alias=data_db_alias)
        self.report_data = report_data

    def _create_excel_report(self):
        if self.report_data is not None:
            return self._create_excel_report_from_data(self.report_data)

        toimipaikka_filter = get_active_filter(self._target_date())

        vakajarjestaja_filter = Q(vakajarjestaja=self.organisaatio_id) | (
            Q(paos_toiminnat_paos_toimipaikka__oma_organisaatio=self.organisaatio_id)
            & Q(paos_toiminnat_paos_toimipaikka__voimassa_kytkin=True)
        )
        if self.toimipaikka_id:
            vakajarjestaja_filter &= Q(id=self.toimipaikka_id)

        toimipaikka_qs = (
            Toimipaikka.objects.filter(vakajarjestaja_filter & toimipaikka_filter)
            .select_related("vakajarjestaja")
            .prefetch_related("toiminnallisetpainotukset", "kielipainotukset")
            .distinct()
            .order_by("nimi", "vakajarjestaja_id")
        )

        kunta_codes = self._get_koodisto_with_translations(Koodistot.kunta_koodit.value)
        kasvatusjarjestelma_codes = self._get_koodisto_with_translations(Koodistot.kasvatusopillinen_jarjestelma_koodit.value)
        toiminnallinen_painotus_codes = self._get_koodisto_with_translations(Koodistot.toiminnallinen_painotus_koodit.value)
        kieli_codes = self._get_koodisto_with_translations(Koodistot.kieli_koodit.value)
        kielipainotustyyppi_codes = self._get_koodisto_with_translations(Koodistot.kielipainotustyyppi_koodit.value)
        toimintamuoto_codes = self._get_koodisto_with_translations(Koodistot.toimintamuoto_koodit.value)
        jarjestamismuoto_codes = self._get_koodisto_with_translations(Koodistot.jarjestamismuoto_koodit.value)
        lahdejarjestelma_codes = self._get_koodisto_with_translations(Koodistot.lahdejarjestelma_koodit.value)

        toimipaikka_sheet = self._add_worksheet(T.EXCEL_TOIMIPAIKKA_PLURAL)
        self._write_headers(toimipaikka_sheet, TOIMIPAIKKA_HEADERS)

        index = 1
        for toimipaikka in toimipaikka_qs.iterator(chunk_size=1000):
            painotus_list = list(toimipaikka.toiminnallisetpainotukset.all()) + list(toimipaikka.kielipainotukset.all())
            if len(painotus_list) == 0:
                # We want at least one row for toimipaikka
                painotus_list = [TemporaryObject()]
            for painotus in painotus_list:
                toimipaikka_values = [
                    toimipaikka.nimi,
                    toimipaikka.organisaatio_oid,
                    toimipaikka.id,
                    _get_code_translation(lahdejarjestelma_codes, toimipaikka.lahdejarjestelma),
                    toimipaikka.tunniste,
                ]

                if toimipaikka.vakajarjestaja_id != self.organisaatio_id:
                    toimipaikka_values.extend([toimipaikka.vakajarjestaja.nimi, toimipaikka.vakajarjestaja.organisaatio_oid])
                else:
                    toimipaikka_values.extend([None, None])

                toimipaikka_values.extend(
                    [
                        toimipaikka.alkamis_pvm,
                        toimipaikka.paattymis_pvm,
                        _get_code_translation(kasvatusjarjestelma_codes, toimipaikka.kasvatusopillinen_jarjestelma_koodi),
                        _get_code_translation(toimintamuoto_codes, toimipaikka.toimintamuoto_koodi),
                        _get_multiple_code_translations(kieli_codes, toimipaikka.toimintakieli_koodi),
                        _get_multiple_code_translations(jarjestamismuoto_codes, toimipaikka.jarjestamismuoto_koodi),
                        toimipaikka.varhaiskasvatuspaikat,
                        _get_code_translation(kunta_codes, toimipaikka.kunta_koodi),
                        toimipaikka.kayntiosoite,
                        toimipaikka.kayntiosoite_postinumero,
                        toimipaikka.kayntiosoite_postitoimipaikka,
                        toimipaikka.postiosoite,
                        toimipaikka.postinumero,
                        toimipaikka.postitoimipaikka,
                        toimipaikka.puhelinnumero,
                        toimipaikka.sahkopostiosoite,
                    ]
                )

                # Painotus information
                if not isinstance(painotus, TemporaryObject):
                    toimipaikka_values.extend(
                        [painotus.id, _get_code_translation(lahdejarjestelma_codes, painotus.lahdejarjestelma), painotus.tunniste]
                    )
                    if hasattr(painotus, "toimintapainotus_koodi"):
                        toimipaikka_values.extend(
                            [_get_code_translation(toiminnallinen_painotus_codes, painotus.toimintapainotus_koodi), None, None]
                        )
                    elif hasattr(painotus, "kielipainotus_koodi"):
                        toimipaikka_values.extend(
                            [
                                None,
                                _get_code_translation(kieli_codes, painotus.kielipainotus_koodi),
                                _get_code_translation(kielipainotustyyppi_codes, painotus.kielipainotustyyppi_koodi),
                            ]
                        )
                    toimipaikka_values.extend([painotus.alkamis_pvm, painotus.paattymis_pvm])

                self._write_row(toimipaikka_sheet, index, toimipaikka_values)
                index += 1

    def _create_excel_report_from_data(self, report_data):
        koodistot = report_data["koodistot"]
        toimipaikka_sheet = self._add_worksheet(T.EXCEL_TOIMIPAIKKA_PLURAL)
        self._write_headers(toimipaikka_sheet, TOIMIPAIKKA_HEADERS)

        index = 1
        for toimipaikka in report_data["toimipaikat"]:
            painotus_list = toimipaikka["painotukset"] or [None]
            for painotus in painotus_list:
                toimipaikka_values = [
                    toimipaikka["nimi"],
                    toimipaikka["oid"],
                    toimipaikka["id"],
                    _get_code_translation(koodistot["lahdejarjestelma"], toimipaikka["lahdejarjestelma"]),
                    toimipaikka["tunniste"],
                ]
                palveluntuottaja = toimipaikka["palveluntuottaja"]
                toimipaikka_values.extend(
                    [palveluntuottaja["nimi"], palveluntuottaja["oid"]] if palveluntuottaja else [None, None]
                )
                toimipaikka_values.extend(
                    [
                        toimipaikka["alkamis_pvm"],
                        toimipaikka["paattymis_pvm"],
                        _get_code_translation(
                            koodistot["kasvatusopillinen_jarjestelma"], toimipaikka["kasvatusopillinen_jarjestelma"]
                        ),
                        _get_code_translation(koodistot["toimintamuoto"], toimipaikka["toimintamuoto"]),
                        _get_multiple_code_translations(koodistot["kieli"], toimipaikka["toimintakieli"]),
                        _get_multiple_code_translations(koodistot["jarjestamismuoto"], toimipaikka["jarjestamismuoto"]),
                        toimipaikka["varhaiskasvatuspaikat"],
                        _get_code_translation(koodistot["kunta"], toimipaikka["kunta"]),
                        toimipaikka["kayntiosoite"],
                        toimipaikka["kayntiosoite_postinumero"],
                        toimipaikka["kayntiosoite_postitoimipaikka"],
                        toimipaikka["postiosoite"],
                        toimipaikka["postinumero"],
                        toimipaikka["postitoimipaikka"],
                        toimipaikka["puhelinnumero"],
                        toimipaikka["sahkopostiosoite"],
                    ]
                )
                if painotus:
                    toimipaikka_values.extend(
                        [
                            painotus["id"],
                            _get_code_translation(koodistot["lahdejarjestelma"], painotus["lahdejarjestelma"]),
                            painotus["tunniste"],
                            _get_code_translation(koodistot["toiminnallinen_painotus"], painotus["toiminnallinen_painotus"]),
                            _get_code_translation(koodistot["kieli"], painotus["kielipainotus"]),
                            _get_code_translation(koodistot["kielipainotustyyppi"], painotus["kielipainotuksen_tyyppi"]),
                            painotus["alkamis_pvm"],
                            painotus["paattymis_pvm"],
                        ]
                    )
                self._write_row(toimipaikka_sheet, index, toimipaikka_values)
                index += 1


def load_toimipaikat_voimassa_data(generator):
    toimipaikka_filter = get_active_filter(generator._target_date())
    vakajarjestaja_filter = Q(vakajarjestaja=generator.organisaatio_id) | (
        Q(paos_toiminnat_paos_toimipaikka__oma_organisaatio=generator.organisaatio_id)
        & Q(paos_toiminnat_paos_toimipaikka__voimassa_kytkin=True)
    )
    if generator.toimipaikka_id:
        vakajarjestaja_filter &= Q(id=generator.toimipaikka_id)

    koodisto_nimet = {
        "kunta": Koodistot.kunta_koodit.value,
        "kasvatusopillinen_jarjestelma": Koodistot.kasvatusopillinen_jarjestelma_koodit.value,
        "toiminnallinen_painotus": Koodistot.toiminnallinen_painotus_koodit.value,
        "kieli": Koodistot.kieli_koodit.value,
        "kielipainotustyyppi": Koodistot.kielipainotustyyppi_koodit.value,
        "toimintamuoto": Koodistot.toimintamuoto_koodit.value,
        "jarjestamismuoto": Koodistot.jarjestamismuoto_koodit.value,
        "lahdejarjestelma": Koodistot.lahdejarjestelma_koodit.value,
    }
    koodistot = {name: generator._get_koodisto_with_translations(value) for name, value in koodisto_nimet.items()}
    toimipaikat = []
    toimipaikka_qs = (
        Toimipaikka.objects.using(generator.data_db_alias)
        .filter(vakajarjestaja_filter & toimipaikka_filter)
        .select_related("vakajarjestaja")
        .prefetch_related("toiminnallisetpainotukset", "kielipainotukset")
        .distinct()
        .order_by("nimi", "vakajarjestaja_id")
    )
    for toimipaikka in toimipaikka_qs.iterator(chunk_size=1000):
        toimipaikat.append(
            {
                "nimi": toimipaikka.nimi,
                "oid": toimipaikka.organisaatio_oid,
                "id": toimipaikka.id,
                "lahdejarjestelma": toimipaikka.lahdejarjestelma,
                "tunniste": toimipaikka.tunniste,
                "palveluntuottaja": (
                    {"nimi": toimipaikka.vakajarjestaja.nimi, "oid": toimipaikka.vakajarjestaja.organisaatio_oid}
                    if toimipaikka.vakajarjestaja_id != generator.organisaatio_id
                    else None
                ),
                "alkamis_pvm": toimipaikka.alkamis_pvm,
                "paattymis_pvm": toimipaikka.paattymis_pvm,
                "kasvatusopillinen_jarjestelma": toimipaikka.kasvatusopillinen_jarjestelma_koodi,
                "toimintamuoto": toimipaikka.toimintamuoto_koodi,
                "toimintakieli": toimipaikka.toimintakieli_koodi,
                "jarjestamismuoto": toimipaikka.jarjestamismuoto_koodi,
                "varhaiskasvatuspaikat": toimipaikka.varhaiskasvatuspaikat,
                "kunta": toimipaikka.kunta_koodi,
                "kayntiosoite": toimipaikka.kayntiosoite,
                "kayntiosoite_postinumero": toimipaikka.kayntiosoite_postinumero,
                "kayntiosoite_postitoimipaikka": toimipaikka.kayntiosoite_postitoimipaikka,
                "postiosoite": toimipaikka.postiosoite,
                "postinumero": toimipaikka.postinumero,
                "postitoimipaikka": toimipaikka.postitoimipaikka,
                "puhelinnumero": toimipaikka.puhelinnumero,
                "sahkopostiosoite": toimipaikka.sahkopostiosoite,
                "painotukset": [
                    {
                        "id": painotus.id,
                        "lahdejarjestelma": painotus.lahdejarjestelma,
                        "tunniste": painotus.tunniste,
                        "toiminnallinen_painotus": getattr(painotus, "toimintapainotus_koodi", None),
                        "kielipainotus": getattr(painotus, "kielipainotus_koodi", None),
                        "kielipainotuksen_tyyppi": getattr(painotus, "kielipainotustyyppi_koodi", None),
                        "alkamis_pvm": painotus.alkamis_pvm,
                        "paattymis_pvm": painotus.paattymis_pvm,
                    }
                    for painotus in list(toimipaikka.toiminnallisetpainotukset.all()) + list(toimipaikka.kielipainotukset.all())
                ],
            }
        )
    return {"toimipaikat": toimipaikat, "koodistot": koodistot}


def create_toimipaikat_voimassa_json_from_data(report_data):
    koodistot = report_data["koodistot"]
    toimipaikat = []
    for toimipaikka_data in report_data["toimipaikat"]:
        toimipaikka = {
            "nimi": toimipaikka_data["nimi"],
            "oid": toimipaikka_data["oid"],
            "id": toimipaikka_data["id"],
            "lahdejarjestelma": _get_json_code_translation(koodistot["lahdejarjestelma"], toimipaikka_data["lahdejarjestelma"]),
            "tunniste": toimipaikka_data["tunniste"],
            "palveluntuottaja": toimipaikka_data["palveluntuottaja"],
            "alkamis_pvm": toimipaikka_data["alkamis_pvm"].isoformat() if toimipaikka_data["alkamis_pvm"] else None,
            "paattymis_pvm": toimipaikka_data["paattymis_pvm"].isoformat() if toimipaikka_data["paattymis_pvm"] else None,
            "kasvatusopillinen_jarjestelma": _get_json_code_translation(
                koodistot["kasvatusopillinen_jarjestelma"], toimipaikka_data["kasvatusopillinen_jarjestelma"]
            ),
            "toimintamuoto": _get_json_code_translation(koodistot["toimintamuoto"], toimipaikka_data["toimintamuoto"]),
            "toimintakieli": [_get_json_code_translation(koodistot["kieli"], code) for code in toimipaikka_data["toimintakieli"]],
            "jarjestamismuoto": [
                _get_json_code_translation(koodistot["jarjestamismuoto"], code) for code in toimipaikka_data["jarjestamismuoto"]
            ],
            "varhaiskasvatuspaikat": toimipaikka_data["varhaiskasvatuspaikat"],
            "kunta": _get_json_code_translation(koodistot["kunta"], toimipaikka_data["kunta"]),
            "kayntiosoite": toimipaikka_data["kayntiosoite"],
            "kayntiosoite_postinumero": toimipaikka_data["kayntiosoite_postinumero"],
            "kayntiosoite_postitoimipaikka": toimipaikka_data["kayntiosoite_postitoimipaikka"],
            "postiosoite": toimipaikka_data["postiosoite"],
            "postinumero": toimipaikka_data["postinumero"],
            "postitoimipaikka": toimipaikka_data["postitoimipaikka"],
            "puhelinnumero": toimipaikka_data["puhelinnumero"],
            "sahkopostiosoite": toimipaikka_data["sahkopostiosoite"],
            "painotukset": [],
        }
        for painotus in toimipaikka_data["painotukset"]:
            toimipaikka["painotukset"].append(
                {
                    "id": painotus["id"],
                    "lahdejarjestelma": _get_json_code_translation(koodistot["lahdejarjestelma"], painotus["lahdejarjestelma"]),
                    "tunniste": painotus["tunniste"],
                    "toiminnallinen_painotus": _get_json_code_translation(
                        koodistot["toiminnallinen_painotus"], painotus["toiminnallinen_painotus"]
                    ),
                    "kielipainotus": _get_json_code_translation(koodistot["kieli"], painotus["kielipainotus"]),
                    "kielipainotuksen_tyyppi": _get_json_code_translation(
                        koodistot["kielipainotustyyppi"], painotus["kielipainotuksen_tyyppi"]
                    ),
                    "alkamis_pvm": painotus["alkamis_pvm"].isoformat() if painotus["alkamis_pvm"] else None,
                    "paattymis_pvm": painotus["paattymis_pvm"].isoformat() if painotus["paattymis_pvm"] else None,
                }
            )
        toimipaikat.append(toimipaikka)
    return {"raportti": ExcelReportType.TOIMIPAIKAT_VOIMASSA.value, "schema_version": 1, "toimipaikat": toimipaikat}
