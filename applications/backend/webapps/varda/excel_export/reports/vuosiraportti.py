import datetime

from varda.constants import YRITYSMUOTO_KUNTA
from varda.enums.koodistot import Koodistot
from varda.enums.translation import Translation as T
from varda.excel_export.base import BaseExcelReportGenerator
from varda.excel_export.constants import ExcelReportSubtype
from varda.excel_export.utils import _get_code_translation, _get_nested_value
from varda.misc import get_latest_tilastointi_pvm_before_date, get_tuen_tiedot_tuen_taso_paatosmaaras
from varda.misc_queries import (
    get_koodisto_codes_lower,
    get_yearly_report_fixed_term_data,
    get_yearly_report_kielipainotus_data,
    get_yearly_report_lapsi_ids,
    get_yearly_report_maksutieto_data,
    get_yearly_report_organisaatio_count,
    get_yearly_report_palvelussuhde_data,
    get_yearly_report_toiminnallinen_painotus_count,
    get_yearly_report_toimintakieli_data,
    get_yearly_report_toimipaikka_data,
    get_yearly_report_tyontekija_ids,
    get_yearly_report_tyontekija_multiple_tehtavanimike_count,
    get_yearly_report_tyoskentelypaikka_data,
    get_yearly_report_vaka_data,
    get_yearly_report_vuokrattu_henkilosto_data,
)

VUOSIRAPORTTI_VARHAISKASVATUS_HEADERS = (
    "",
    T.EXCEL_KAIKKI_TIEDOT,
    T.EXCEL_OMAT_TIEDOT,
    T.EXCEL_PAOS_TIEDOT,
)

FILENAME_KEYS = {
    ExcelReportSubtype.ALL.value: T.EXCEL_FILENAME_VUOSIRAPORTTI_ALL,
    ExcelReportSubtype.VARHAISKASVATUS.value: T.EXCEL_FILENAME_VUOSIRAPORTTI_VARHAISKASVATUS,
    ExcelReportSubtype.HENKILOSTO.value: T.EXCEL_FILENAME_VUOSIRAPORTTI_HENKILOSTO,
}


class VuosiraporttiReportGenerator(BaseExcelReportGenerator):
    def _get_filename_key(self):
        return FILENAME_KEYS[self.report.report_subtype]

    def _create_excel_report(self):
        tilasto_date = self.report.target_date
        poiminta_time = datetime.time(hour=23, minute=0, second=0)
        poiminta_datetime = datetime.datetime.combine(self.report.target_date_secondary, poiminta_time, datetime.timezone.utc)
        if self.report.report_subtype in (ExcelReportSubtype.ALL.value, ExcelReportSubtype.VARHAISKASVATUS.value):
            self._create_varhaiskasvatus_sheet(tilasto_date, poiminta_datetime)
        if self.report.report_subtype in (ExcelReportSubtype.ALL.value, ExcelReportSubtype.HENKILOSTO.value):
            self._create_henkilosto_sheet(tilasto_date, poiminta_datetime)

    def _write_organisaatio_rows(self, sheet, index, tilasto_date, poiminta_datetime):
        if organisaatio := self.report.organisaatio:
            organisaatio_count = 1
            if organisaatio.paattymis_pvm is None:
                organisaatio_active = organisaatio.alkamis_pvm <= tilasto_date
            else:
                organisaatio_active = organisaatio.alkamis_pvm <= tilasto_date <= organisaatio.paattymis_pvm
        else:
            organisaatio_count = get_yearly_report_organisaatio_count(poiminta_datetime, tilasto_date)
            organisaatio_active = True

        self._write_row(sheet, index, [self._get_translation(T.EXCEL_VAKATOIMIJA_VALITTU_PLURAL), organisaatio_count])
        index += 1
        self._write_row(
            sheet,
            index,
            [self._get_translation(T.EXCEL_VAKATOIMIJA_NIMI), getattr(organisaatio, "nimi", "")],
            align_right_index_list=[1],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [self._get_translation(T.EXCEL_VAKATOIMIJA_VOIMASSA), self._get_boolean_translation(organisaatio_active)],
            align_right_index_list=[1],
        )
        index += 2
        return index

    def _create_varhaiskasvatus_sheet(self, tilasto_date, poiminta_datetime):
        sheet = self._add_worksheet(T.EXCEL_VARHAISKASVATUSTIEDOT)
        self._write_headers(sheet, VUOSIRAPORTTI_VARHAISKASVATUS_HEADERS)
        organisaatio = self.report.organisaatio
        index = self._write_organisaatio_rows(sheet, 1, tilasto_date, poiminta_datetime)

        toimipaikka_data = get_yearly_report_toimipaikka_data(poiminta_datetime, tilasto_date, self.organisaatio_id)
        toimipaikka_count = toimipaikka_data.pop("toimipaikka_count")
        varhaiskasvatuspaikat_sum = toimipaikka_data.pop("varhaiskasvatuspaikat_sum")
        toimipaikka_by_toimintamuoto_count = toimipaikka_data

        self._write_row(sheet, index, [self._get_translation(T.EXCEL_TOIMIPAIKKA_PLURAL), toimipaikka_count])
        index += 1
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_VARHAISKASVATUSPAIKAT_MAARA), varhaiskasvatuspaikat_sum])
        index += 1

        toiminnallinen_painotus_count = get_yearly_report_toiminnallinen_painotus_count(
            poiminta_datetime, tilasto_date, self.organisaatio_id
        )
        self._write_row(
            sheet, index, [self._get_translation(T.EXCEL_TOIMINNALLINEN_PAINOTUS_PLURAL), toiminnallinen_painotus_count]
        )
        index += 2

        tm_translations = self._get_koodisto_with_translations(Koodistot.toimintamuoto_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_TOIMIPAIKKA_BY_TOIMINTAMUOTO)])
        index += 1
        for key, value in toimipaikka_by_toimintamuoto_count.items():
            self._write_row(sheet, index, [_get_code_translation(tm_translations, key), value])
            index += 1
        index += 1

        index = self._write_kielipainotus_data(sheet, index, poiminta_datetime, tilasto_date)
        index += 1

        index = self._write_toimintakieli_data(sheet, index, poiminta_datetime, tilasto_date)
        index += 1

        lapsi_id_data = get_yearly_report_lapsi_ids(poiminta_datetime, tilasto_date, self.organisaatio_id)
        lapsi_id_list = lapsi_id_data["lapsi_id_array"]
        varhaiskasvatussuhde_id_list = lapsi_id_data["varhaiskasvatussuhde_id_array"]

        # Nested dict: {paos (None, False): {toimintamuoto (None, 'tm01'): {...}}}
        vaka_data = get_yearly_report_vaka_data(poiminta_datetime, varhaiskasvatussuhde_id_list)

        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_HENKILO_PLURAL),
                _get_nested_value(vaka_data, [None, None], "henkilo_count"),
                _get_nested_value(vaka_data, [False, None], "henkilo_count"),
                _get_nested_value(vaka_data, [True, None], "henkilo_count"),
            ],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_LAPSI_PLURAL),
                _get_nested_value(vaka_data, [None, None], "lapsi_count"),
                _get_nested_value(vaka_data, [False, None], "lapsi_count"),
                _get_nested_value(vaka_data, [True, None], "lapsi_count"),
            ],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_LAPSI_OSAPAIVAINEN),
                _get_nested_value(vaka_data, [None, None], "osapaivainen_count"),
                _get_nested_value(vaka_data, [False, None], "osapaivainen_count"),
                _get_nested_value(vaka_data, [True, None], "osapaivainen_count"),
            ],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_LAPSI_KOKOPAIVAINEN),
                _get_nested_value(vaka_data, [None, None], "kokopaivainen_count"),
                _get_nested_value(vaka_data, [False, None], "kokopaivainen_count"),
                _get_nested_value(vaka_data, [True, None], "kokopaivainen_count"),
            ],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_LAPSI_VUOROHOITO),
                _get_nested_value(vaka_data, [None, None], "vuorohoito_count"),
                _get_nested_value(vaka_data, [False, None], "vuorohoito_count"),
                _get_nested_value(vaka_data, [True, None], "vuorohoito_count"),
            ],
        )
        index += 2

        tm_codes = get_koodisto_codes_lower(Koodistot.toimintamuoto_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_LAPSI_BY_TOIMINTAMUOTO)])
        index += 1
        for tm_code in tm_codes:
            code_translation = _get_code_translation(tm_translations, tm_code)
            self._write_row(
                sheet,
                index,
                [
                    code_translation,
                    _get_nested_value(vaka_data, [None, tm_code], "lapsi_count"),
                    _get_nested_value(vaka_data, [False, tm_code], "lapsi_count"),
                    _get_nested_value(vaka_data, [True, tm_code], "lapsi_count"),
                ],
            )
            index += 1
        index += 1

        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_VARHAISKASVATUSSUHDE_PLURAL),
                _get_nested_value(vaka_data, [None, None], "suhde_count"),
                _get_nested_value(vaka_data, [False, None], "suhde_count"),
                _get_nested_value(vaka_data, [True, None], "suhde_count"),
            ],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_VARHAISKASVATUSPAATOS_PLURAL),
                _get_nested_value(vaka_data, [None, None], "paatos_count"),
                _get_nested_value(vaka_data, [False, None], "paatos_count"),
                _get_nested_value(vaka_data, [True, None], "paatos_count"),
            ],
        )
        index += 2

        # Nested dict: {paos (None, True, False): {maksun_peruste (None, 'mp01', 'mp02', 'mp03'): {...}}}
        maksutieto_data = get_yearly_report_maksutieto_data(poiminta_datetime, tilasto_date, self.organisaatio_id, lapsi_id_list)

        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_MAKSUTIETO_PLURAL),
                _get_nested_value(maksutieto_data, [None, None], "count"),
                _get_nested_value(maksutieto_data, [False, None], "count"),
                _get_nested_value(maksutieto_data, [True, None], "count"),
            ],
        )
        index += 2

        mp_codes = get_koodisto_codes_lower(Koodistot.maksun_peruste_koodit.value)
        mp_translations = self._get_koodisto_with_translations(Koodistot.maksun_peruste_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_MAKSUTIETO_BY_MAKSUN_PERUSTE)])
        index += 1
        for mp_code in mp_codes:
            self._write_row(
                sheet,
                index,
                [
                    _get_code_translation(mp_translations, mp_code),
                    _get_nested_value(maksutieto_data, [None, mp_code], "count"),
                    _get_nested_value(maksutieto_data, [False, mp_code], "count"),
                    _get_nested_value(maksutieto_data, [True, mp_code], "count"),
                ],
            )
            index += 1
        index += 1

        # Add tuen tiedot data if organisaatio is kunta
        if organisaatio is not None:
            organisaatio_yritysmuoto = getattr(organisaatio, "yritysmuoto", "")
        else:
            organisaatio_yritysmuoto = ""

        if organisaatio_yritysmuoto in YRITYSMUOTO_KUNTA:
            latest_tilastointi_pvm = get_latest_tilastointi_pvm_before_date(organisaatio, tilasto_date)
            paatosmaaras = get_tuen_tiedot_tuen_taso_paatosmaaras(organisaatio, latest_tilastointi_pvm)

            self._write_row(
                sheet,
                index,
                [
                    self._get_translation(T.EXCEL_TUEN_HALLINTOPAATOKSET),
                    paatosmaaras["total"] if paatosmaaras["total"] is not None else "-",
                ],
            )
            index += 1
            self._write_row(
                sheet,
                index,
                [self._get_translation(T.EXCEL_TILASTOINTIPAIVAMAARA), latest_tilastointi_pvm if latest_tilastointi_pvm else "-"],
            )
            index += 2
            self._write_row(sheet, index, [self._get_translation(T.EXCEL_TUKIPAATOSTIEDOT)])
            index += 1
            for tuentaso_code in ["TT01", "TT02", "TT03"]:
                self._write_row(
                    sheet,
                    index,
                    [
                        self._get_translation(getattr(T, f"EXCEL_TUENTASO_{tuentaso_code}")),
                        paatosmaaras[tuentaso_code] if paatosmaaras[tuentaso_code] is not None else "-",
                    ],
                )
                index += 1

    def _create_henkilosto_sheet(self, tilasto_date, poiminta_datetime):
        sheet = self._add_worksheet(T.EXCEL_HENKILOSTOTIEDOT)
        index = self._write_organisaatio_rows(sheet, 0, tilasto_date, poiminta_datetime)

        tyontekija_id_data = get_yearly_report_tyontekija_ids(poiminta_datetime, tilasto_date, self.organisaatio_id)
        palvelussuhde_id_list = tyontekija_id_data["palvelussuhde_id_array"]
        tyoskentelypaikka_id_list = tyontekija_id_data["tyoskentelypaikka_id_array"]

        # Nested dict: {tehtavanimike (None, '12345'): {...}}
        tyoskentelypaikka_data = get_yearly_report_tyoskentelypaikka_data(poiminta_datetime, tyoskentelypaikka_id_list)

        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_TYONTEKIJA_PLURAL),
                _get_nested_value(tyoskentelypaikka_data, [None], "henkilo_count"),
            ],
        )
        index += 1

        multiple_tehtavanimike_count = get_yearly_report_tyontekija_multiple_tehtavanimike_count(
            poiminta_datetime, tyoskentelypaikka_id_list
        )
        self._write_row(
            sheet, index, [self._get_translation(T.EXCEL_TYONTEKIJA_TEHTAVANIMIKE_MULTIPLE), multiple_tehtavanimike_count]
        )
        index += 2

        tn_codes = get_koodisto_codes_lower(Koodistot.tehtavanimike_koodit.value)
        tn_translations = self._get_koodisto_with_translations(Koodistot.tehtavanimike_koodit.value)
        index_temp = index + len(tn_codes) + 2
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_TYONTEKIJA_BY_TEHTAVANIMIKE)])
        index += 1
        self._write_row(sheet, index_temp, [self._get_translation(T.EXCEL_TYONTEKIJA_KELPOINEN_BY_TEHTAVANIMIKE)])
        index_temp += 1

        for tn_code in tn_codes:
            code_translation = _get_code_translation(tn_translations, tn_code)
            count = _get_nested_value(tyoskentelypaikka_data, [tn_code], "henkilo_count")
            kelpoiset_count = _get_nested_value(tyoskentelypaikka_data, [tn_code], "henkilo_kelpoinen_count")
            self._write_row(sheet, index, [code_translation, count])
            index += 1
            self._write_row(sheet, index_temp, [code_translation, kelpoiset_count])
            index_temp += 1
        index = index_temp + 1

        # Nested dict: {tyosuhde (None, '1', '2'): {tyoaika (None, '1', '2'): {...}}}
        palvelussuhde_data = get_yearly_report_palvelussuhde_data(poiminta_datetime, palvelussuhde_id_list)

        ts_codes = get_koodisto_codes_lower(Koodistot.tyosuhde_koodit.value)
        ts_translations = self._get_koodisto_with_translations(Koodistot.tyosuhde_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_PALVELUSSUHDE_BY_TYOSUHDE)])
        index += 1
        for ts_code in ts_codes:
            count = _get_nested_value(palvelussuhde_data, [ts_code, None], "palvelussuhde_count")
            self._write_row(sheet, index, [_get_code_translation(ts_translations, ts_code), count])
            index += 1
        index += 1

        ta_codes = get_koodisto_codes_lower(Koodistot.tyoaika_koodit.value)
        ta_translations = self._get_koodisto_with_translations(Koodistot.tyoaika_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_PALVELUSSUHDE_BY_TYOAIKA)])
        index += 1
        for ta_code in ta_codes:
            count = _get_nested_value(palvelussuhde_data, [None, ta_code], "palvelussuhde_count")
            self._write_row(sheet, index, [_get_code_translation(ta_translations, ta_code), count])
            index += 1
        index += 1

        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_TYONTEKIJA_KIERTAVA_PLURAL),
                _get_nested_value(tyoskentelypaikka_data, [None], "henkilo_kiertava_count"),
            ],
        )
        index += 2

        vuokrattu_henkilosto_data = get_yearly_report_vuokrattu_henkilosto_data(
            poiminta_datetime, tilasto_date, self.organisaatio_id
        )

        self._write_row(
            sheet, index, [self._get_translation(T.EXCEL_VUOKRATTU_HENKILOSTO_TYONTEKIJAMAARA), vuokrattu_henkilosto_data[0]]
        )
        index += 1
        self._write_row(
            sheet, index, [self._get_translation(T.EXCEL_VUOKRATTU_HENKILOSTO_TUNTIMAARA), vuokrattu_henkilosto_data[1]]
        )
        index += 2

        month_translation_list = [
            self._get_translation(T.EXCEL_JANUARY),
            self._get_translation(T.EXCEL_FEBRUARY),
            self._get_translation(T.EXCEL_MARCH),
            self._get_translation(T.EXCEL_APRIL),
            self._get_translation(T.EXCEL_MAY),
            self._get_translation(T.EXCEL_JUNE),
            self._get_translation(T.EXCEL_JULY),
            self._get_translation(T.EXCEL_AUGUST),
            self._get_translation(T.EXCEL_SEPTEMBER),
            self._get_translation(T.EXCEL_OCTOBER),
            self._get_translation(T.EXCEL_NOVEMBER),
            self._get_translation(T.EXCEL_DECEMBER),
        ]
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_FIXED_TERM_EMPLOYMENT)])
        index += 1

        # Form 13 rows for full year and monthly numbers
        term_count = get_yearly_report_fixed_term_data(poiminta_datetime, tilasto_date.year, self.organisaatio_id)

        self._write_row(sheet, index, [self._get_translation(T.EXCEL_WHOLE_YEAR), term_count[0][1]])
        index += 1
        for month_index in range(1, 13):
            self._write_row(sheet, index, [month_translation_list[month_index - 1], term_count[month_index][1]])
            index += 1

    def _write_kielipainotus_data(self, sheet, index, poiminta_datetime, tilasto_date):
        kielipainotus_data = get_yearly_report_kielipainotus_data(poiminta_datetime, tilasto_date, self.organisaatio_id)
        kielipainotus_count = kielipainotus_data.pop("kielipainotus_count")
        kielipainotus_count_by_kielipainotus_tyyppi = kielipainotus_data
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_KIELIPAINOTUS_PLURAL), kielipainotus_count])
        index += 1

        kp_translations = self._get_koodisto_with_translations(Koodistot.kielipainotustyyppi_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_KIELIPAINOTUS_PLURAL_TYYPPI_PLURAL)])
        index += 1
        for key, value in kielipainotus_count_by_kielipainotus_tyyppi.items():
            self._write_row(sheet, index, [_get_code_translation(kp_translations, key), value])
            index += 1

        return index

    def _write_toimintakieli_data(self, sheet, index, poiminta_datetime, tilasto_date):
        toimintakieli_data = get_yearly_report_toimintakieli_data(poiminta_datetime, tilasto_date, self.organisaatio_id)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_TOIMINTAKIELI)])
        index += 1

        kieli_codes = self._get_koodisto_with_translations(Koodistot.kieli_koodit.value)
        for toimintakieli_obj in toimintakieli_data:
            key = toimintakieli_obj["language_code"]
            value = toimintakieli_obj["value"]
            self._write_row(sheet, index, [_get_code_translation(kieli_codes, key), value])
            index += 1

        return index
