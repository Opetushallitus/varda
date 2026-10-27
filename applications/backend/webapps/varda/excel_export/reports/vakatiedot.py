import datetime

from django.db.models import F, Q

from varda.enums.koodistot import Koodistot
from varda.enums.translation import Translation as T
from varda.excel_export.base import BaseExcelReportGenerator
from varda.excel_export.utils import _get_code_translation
from varda.misc import decrypt_henkilotunnus
from varda.misc_queries import get_active_filter, get_inactive_filter
from varda.models import Maksutieto, Varhaiskasvatussuhde

# Custom headers used sometimes for specific customer requests, to be modified based on request
# Remember to update vakasuhde_values in VakatiedotVoimassaReportGenerator as well - for row writing
VAKASUHDE_HEADERS_CUSTOM = (
    T.EXCEL_OPPIJANUMERO,
    T.EXCEL_HETU,
)

VAKASUHDE_HEADERS = (
    T.EXCEL_OPPIJANUMERO,
    T.EXCEL_ETUNIMET,
    T.EXCEL_SUKUNIMI,
    T.EXCEL_HETU,
    T.EXCEL_TURVAKIELTO,
    T.EXCEL_LAPSI_ID,
    T.EXCEL_PAOS_KYTKIN,
    T.EXCEL_PAOS_NIMI,
    T.EXCEL_PAOS_OID,
    T.EXCEL_LAHDEJARJESTELMA,
    T.EXCEL_VARHAISKASVATUSPAATOS_ID,
    T.EXCEL_HAKEMUS_PVM,
    T.EXCEL_ALKAMIS_PVM,
    T.EXCEL_PAATTYMIS_PVM,
    T.EXCEL_JARJESTAMISMUOTO,
    T.EXCEL_PAIVITTAINEN_KYTKIN,
    T.EXCEL_KOKOPAIVAINEN_KYTKIN,
    T.EXCEL_VUOROHOITO_KYTKIN,
    T.EXCEL_TUNTIMAARA_VIIKOSSA,
    T.EXCEL_TILAPAINEN_KYTKIN,
    T.EXCEL_VARHAISKASVATUSSUHDE_ID,
    T.EXCEL_ALKAMIS_PVM,
    T.EXCEL_PAATTYMIS_PVM,
    T.EXCEL_TOIMIPAIKKA_NIMI,
    T.EXCEL_TOIMIPAIKKA_OID,
    T.EXCEL_TOIMIPAIKKA_ID,
)

VAKASUHDE_HEADERS_8Y_OLDER = (
    T.EXCEL_OPPIJANUMERO,
    T.EXCEL_ETUNIMET,
    T.EXCEL_SUKUNIMI,
    T.EXCEL_HETU,
    T.EXCEL_TURVAKIELTO,
    T.EXCEL_LAPSI_ID,
    T.EXCEL_PAOS_KYTKIN,
    T.EXCEL_PAOS_NIMI,
    T.EXCEL_PAOS_OID,
    T.EXCEL_LAHDEJARJESTELMA,
    T.EXCEL_VARHAISKASVATUSPAATOS_ID,
    T.EXCEL_HAKEMUS_PVM,
    T.EXCEL_ALKAMIS_PVM,
    T.EXCEL_PAATTYMIS_PVM,
    T.EXCEL_JARJESTAMISMUOTO,
    T.EXCEL_PAIVITTAINEN_KYTKIN,
    T.EXCEL_KOKOPAIVAINEN_KYTKIN,
    T.EXCEL_VUOROHOITO_KYTKIN,
    T.EXCEL_TUNTIMAARA_VIIKOSSA,
    T.EXCEL_TILAPAINEN_KYTKIN,
    T.EXCEL_VARHAISKASVATUSSUHDE_ID,
    T.EXCEL_ALKAMIS_PVM,
    T.EXCEL_PAATTYMIS_PVM,
    T.EXCEL_VAKATOIMIJA_NIMI,
    T.EXCEL_VAKATOIMIJA_OID,
    T.EXCEL_TOIMIPAIKKA_NIMI,
    T.EXCEL_TOIMIPAIKKA_OID,
    T.EXCEL_TOIMIPAIKKA_ID,
)

MAKSUTIETO_HEADERS = (
    T.EXCEL_OPPIJANUMERO,
    T.EXCEL_ETUNIMET,
    T.EXCEL_SUKUNIMI,
    T.EXCEL_HETU,
    T.EXCEL_TURVAKIELTO,
    T.EXCEL_LAPSI_ID,
    T.EXCEL_PAOS_KYTKIN,
    T.EXCEL_PAOS_NIMI,
    T.EXCEL_PAOS_OID,
    T.EXCEL_MAKSUTIETO_ID,
    T.EXCEL_ALKAMIS_PVM,
    T.EXCEL_PAATTYMIS_PVM,
    T.EXCEL_PERHEEN_KOKO,
    T.EXCEL_MAKSUN_PERUSTE,
    T.EXCEL_ASIAKASMAKSU,
    T.EXCEL_PALVELUSETELI_ARVO,
    T.EXCEL_HUOLTAJA_OPPIJANUMERO,
    T.EXCEL_HUOLTAJA_ETUNIMET,
    T.EXCEL_HUOLTAJA_SUKUNIMI,
)


class VakatiedotVoimassaReportGenerator(BaseExcelReportGenerator):
    filename_key = T.EXCEL_FILENAME_VAKATIEDOT_VOIMASSA

    def _create_excel_report(self):
        target_date = self._target_date()

        active_filter = get_active_filter(target_date)
        vakasuhde_filter = active_filter & get_active_filter(target_date, prefix="varhaiskasvatuspaatos")
        maksutieto_filter = (
            active_filter
            & get_active_filter(target_date, prefix="huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset")
            & get_active_filter(target_date, prefix="huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet")
        )

        self._write_vakasuhde_sheet(vakasuhde_filter)

        if not self.toimipaikka_id and not self.admin_user_all_organizations:
            # Get maksutiedot only on Vakajarjestaja-level, and never for admin_user_all_organizations
            self._write_maksutieto_sheet(maksutieto_filter)

    def _write_vakasuhde_sheet(self, vakasuhde_filter):
        if self.admin_user_all_organizations:
            vakajarjestaja_filter = Q()
            select_related = ["varhaiskasvatuspaatos", "varhaiskasvatuspaatos__lapsi", "varhaiskasvatuspaatos__lapsi__henkilo"]
            order_by = ["varhaiskasvatuspaatos__lapsi__henkilo__id"]
        else:
            vakajarjestaja_filter = (
                Q(varhaiskasvatuspaatos__lapsi__vakatoimija=self.organisaatio_id)
                | Q(varhaiskasvatuspaatos__lapsi__oma_organisaatio=self.organisaatio_id)
                | Q(varhaiskasvatuspaatos__lapsi__paos_organisaatio=self.organisaatio_id)
            )
            select_related = [
                "toimipaikka",
                "toimipaikka__vakajarjestaja",
                "varhaiskasvatuspaatos",
                "varhaiskasvatuspaatos__lapsi",
                "varhaiskasvatuspaatos__lapsi__henkilo",
                "varhaiskasvatuspaatos__lapsi__oma_organisaatio",
                "varhaiskasvatuspaatos__lapsi__paos_organisaatio",
            ]
            order_by = ["varhaiskasvatuspaatos__lapsi__henkilo__sukunimi", "varhaiskasvatuspaatos__lapsi__henkilo__etunimet"]
        if self.toimipaikka_id:
            vakajarjestaja_filter &= Q(toimipaikka=self.toimipaikka_id)

        vakasuhde_qs = (
            Varhaiskasvatussuhde.objects.filter(vakajarjestaja_filter & vakasuhde_filter)
            .select_related(*select_related)
            .distinct()
            .order_by(*order_by)
        )

        jarjestamismuoto_codes = self._get_koodisto_with_translations(Koodistot.jarjestamismuoto_koodit.value)
        lahdejarjestelma_codes = self._get_koodisto_with_translations(Koodistot.lahdejarjestelma_koodit.value)

        vakasuhde_sheet = self._add_worksheet(T.EXCEL_VARHAISKASVATUS)

        if self.admin_user_all_organizations:
            self._write_headers(vakasuhde_sheet, VAKASUHDE_HEADERS_CUSTOM)
        else:
            self._write_headers(vakasuhde_sheet, VAKASUHDE_HEADERS)

        for index, vakasuhde in enumerate(vakasuhde_qs.iterator(), 1):
            vakapaatos = vakasuhde.varhaiskasvatuspaatos
            lapsi = vakapaatos.lapsi
            henkilo = lapsi.henkilo

            if self.admin_user_all_organizations:
                """
                This is a custom selection for specific customer requests. Must match with the VAKASUHDE_HEADERS_CUSTOM
                """
                vakasuhde_values = [
                    henkilo.henkilo_oid,
                    decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id, raise_error=False),
                ]
            else:
                # Lapsi information
                vakasuhde_values = [
                    henkilo.henkilo_oid,
                    henkilo.etunimet,
                    henkilo.sukunimi,
                    decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id, raise_error=False),
                    self._get_boolean_translation(henkilo.turvakielto),
                    lapsi.id,
                    self._get_boolean_translation(lapsi.paos_kytkin),
                ]

                if lapsi.paos_kytkin:
                    paos_organisaatio = (
                        lapsi.paos_organisaatio if self.organisaatio_id != lapsi.paos_organisaatio else lapsi.oma_organisaatio
                    )
                    vakasuhde_values.extend([paos_organisaatio.nimi, paos_organisaatio.organisaatio_oid])
                else:
                    vakasuhde_values.extend([None, None])

                vakasuhde_values.extend([_get_code_translation(lahdejarjestelma_codes, lapsi.lahdejarjestelma)])

                # Vakapaatos information
                vakasuhde_values.extend(
                    [
                        vakapaatos.id,
                        vakapaatos.hakemus_pvm,
                        vakapaatos.alkamis_pvm,
                        vakapaatos.paattymis_pvm,
                        _get_code_translation(jarjestamismuoto_codes, vakapaatos.jarjestamismuoto_koodi),
                        self._get_boolean_translation(vakapaatos.paivittainen_vaka_kytkin),
                        self._get_boolean_translation(vakapaatos.kokopaivainen_vaka_kytkin),
                        self._get_boolean_translation(vakapaatos.vuorohoito_kytkin),
                        vakapaatos.tuntimaara_viikossa,
                        self._get_boolean_translation(vakapaatos.tilapainen_vaka_kytkin),
                    ]
                )

                # Vakasuhde information
                vakasuhde_values.extend(
                    [
                        vakasuhde.id,
                        vakasuhde.alkamis_pvm,
                        vakasuhde.paattymis_pvm,
                        vakasuhde.toimipaikka.nimi,
                        vakasuhde.toimipaikka.organisaatio_oid,
                        vakasuhde.toimipaikka.id,
                    ]
                )

            self.henkilo_id_oid_set.add(
                (
                    henkilo.id,
                    henkilo.henkilo_oid,
                )
            )
            self._write_row(vakasuhde_sheet, index, vakasuhde_values)

    def _write_maksutieto_sheet(self, maksutieto_filter):
        # Get maksutieto only if Lapsi belongs to Vakajarjestaja, or if Vakajarjestaja is oma_organisaatio
        vakajarjestaja_filter = Q(huoltajuussuhteet__lapsi__vakatoimija=self.organisaatio_id) | Q(
            huoltajuussuhteet__lapsi__oma_organisaatio=self.organisaatio_id
        )
        maksutieto_qs = (
            Maksutieto.objects.filter(vakajarjestaja_filter & maksutieto_filter)
            .prefetch_related("huoltajuussuhteet__lapsi__henkilo", "huoltajuussuhteet__huoltaja__henkilo")
            .annotate(
                huoltaja_henkilo_oid=F("huoltajuussuhteet__huoltaja__henkilo__henkilo_oid"),
                huoltaja_etunimet=F("huoltajuussuhteet__huoltaja__henkilo__etunimet"),
                huoltaja_sukunimi=F("huoltajuussuhteet__huoltaja__henkilo__sukunimi"),
                lapsi_id=F("huoltajuussuhteet__lapsi__id"),
                henkilo_id=F("huoltajuussuhteet__lapsi__henkilo_id"),
                henkilo_oid=F("huoltajuussuhteet__lapsi__henkilo__henkilo_oid"),
                etunimet=F("huoltajuussuhteet__lapsi__henkilo__etunimet"),
                sukunimi=F("huoltajuussuhteet__lapsi__henkilo__sukunimi"),
                henkilotunnus=F("huoltajuussuhteet__lapsi__henkilo__henkilotunnus"),
                turvakielto=F("huoltajuussuhteet__lapsi__henkilo__turvakielto"),
                paos_kytkin=F("huoltajuussuhteet__lapsi__paos_kytkin"),
                paos_organisaatio_nimi=F("huoltajuussuhteet__lapsi__paos_organisaatio__nimi"),
                paos_organisaatio_oid=F("huoltajuussuhteet__lapsi__paos_organisaatio__organisaatio_oid"),
            )
            .distinct()
            .order_by("huoltajuussuhteet__lapsi__henkilo__sukunimi", "huoltajuussuhteet__lapsi__henkilo__etunimet")
        )

        maksun_peruste_codes = self._get_koodisto_with_translations(Koodistot.maksun_peruste_koodit.value)

        maksutieto_sheet = self._add_worksheet(T.EXCEL_MAKSUTIETO)
        self._write_headers(maksutieto_sheet, MAKSUTIETO_HEADERS)

        for index, maksutieto in enumerate(maksutieto_qs.iterator(chunk_size=1000), 1):
            # Lapsi information
            maksutieto_values = [
                maksutieto.henkilo_oid,
                maksutieto.etunimet,
                maksutieto.sukunimi,
                decrypt_henkilotunnus(maksutieto.henkilotunnus, henkilo_id=maksutieto.henkilo_id, raise_error=False),
                self._get_boolean_translation(maksutieto.turvakielto),
                maksutieto.lapsi_id,
                self._get_boolean_translation(maksutieto.paos_kytkin),
                maksutieto.paos_organisaatio_nimi,
                maksutieto.paos_organisaatio_oid,
            ]

            # Maksutieto information
            maksutieto_values.extend(
                [
                    maksutieto.id,
                    maksutieto.alkamis_pvm,
                    maksutieto.paattymis_pvm,
                    maksutieto.perheen_koko,
                    _get_code_translation(maksun_peruste_codes, maksutieto.maksun_peruste_koodi),
                    maksutieto.asiakasmaksu,
                    maksutieto.palveluseteli_arvo,
                ]
            )

            # Huoltaja information
            maksutieto_values.extend(
                [maksutieto.huoltaja_henkilo_oid, maksutieto.huoltaja_etunimet, maksutieto.huoltaja_sukunimi]
            )

            self.henkilo_id_oid_set.add(
                (
                    maksutieto.henkilo_id,
                    maksutieto.henkilo_oid,
                )
            )
            self._write_row(maksutieto_sheet, index, maksutieto_values)


class VakatiedotVoimassa8yOlderReportGenerator(BaseExcelReportGenerator):
    filename_key = T.EXCEL_FILENAME_VAKATIEDOT_VOIMASSA_8Y_OLDER

    def _create_excel_report(self):
        target_date = self._target_date()

        active_filter = get_active_filter(target_date)
        inactive_filter = get_inactive_filter(target_date)
        vakasuhde_active_vakapaatos_active_filter = active_filter & get_active_filter(target_date, prefix="varhaiskasvatuspaatos")
        vakasuhde_active_vakapaatos_inactive_filter = active_filter & get_inactive_filter(
            target_date, prefix="varhaiskasvatuspaatos"
        )
        vakasuhde_inactive_vakapaatos_active_filter = inactive_filter & get_active_filter(
            target_date, prefix="varhaiskasvatuspaatos"
        )

        vakajarjestaja_filter = (
            (
                Q(varhaiskasvatuspaatos__lapsi__vakatoimija=self.organisaatio_id)
                | Q(varhaiskasvatuspaatos__lapsi__oma_organisaatio=self.organisaatio_id)
                | Q(varhaiskasvatuspaatos__lapsi__paos_organisaatio=self.organisaatio_id)
            )
            if self.organisaatio_id
            else Q()
        )

        syntyma_pvm_cutoff = target_date - datetime.timedelta(days=365 * 8 + 2)  # 2 leap years
        age_filter = Q(varhaiskasvatuspaatos__lapsi__henkilo__syntyma_pvm__lte=syntyma_pvm_cutoff)

        select_related = [
            "toimipaikka",
            "toimipaikka__vakajarjestaja",
            "varhaiskasvatuspaatos",
            "varhaiskasvatuspaatos__lapsi",
            "varhaiskasvatuspaatos__lapsi__henkilo",
            "varhaiskasvatuspaatos__lapsi__oma_organisaatio",
            "varhaiskasvatuspaatos__lapsi__paos_organisaatio",
        ]
        order_by = [
            "toimipaikka__vakajarjestaja__nimi",
            "varhaiskasvatuspaatos__lapsi__henkilo__sukunimi",
            "varhaiskasvatuspaatos__lapsi__henkilo__etunimet",
        ]

        jarjestamismuoto_codes = self._get_koodisto_with_translations(Koodistot.jarjestamismuoto_koodit.value)
        lahdejarjestelma_codes = self._get_koodisto_with_translations(Koodistot.lahdejarjestelma_koodit.value)

        for sheet in [
            dict(name_key=T.EXCEL_VAKASUHDE_ACTIVE_VAKAPAATOS_ACTIVE, vakasuhde_filter=vakasuhde_active_vakapaatos_active_filter),
            dict(
                name_key=T.EXCEL_VAKASUHDE_ACTIVE_VAKAPAATOS_INACTIVE,
                vakasuhde_filter=vakasuhde_active_vakapaatos_inactive_filter,
            ),
            dict(
                name_key=T.EXCEL_VAKASUHDE_INACTIVE_VAKAPAATOS_ACTIVE,
                vakasuhde_filter=vakasuhde_inactive_vakapaatos_active_filter,
            ),
        ]:
            vakasuhde_sheet = self._add_worksheet(sheet["name_key"])

            self._write_headers(vakasuhde_sheet, VAKASUHDE_HEADERS_8Y_OLDER)

            vakasuhde_qs = (
                Varhaiskasvatussuhde.objects.filter(vakajarjestaja_filter & sheet["vakasuhde_filter"] & age_filter)
                .select_related(*select_related)
                .distinct()
                .order_by(*order_by)
            )

            self._write_rows(vakasuhde_sheet, vakasuhde_qs, jarjestamismuoto_codes, lahdejarjestelma_codes)

    def _write_rows(self, vakasuhde_sheet, vakasuhde_qs, jarjestamismuoto_codes, lahdejarjestelma_codes):
        for index, vakasuhde in enumerate(vakasuhde_qs.iterator(), 1):
            vakapaatos = vakasuhde.varhaiskasvatuspaatos
            lapsi = vakapaatos.lapsi
            henkilo = lapsi.henkilo

            # Lapsi information
            vakasuhde_values = [
                henkilo.henkilo_oid,
                henkilo.etunimet,
                henkilo.sukunimi,
                decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id, raise_error=False),
                self._get_boolean_translation(henkilo.turvakielto),
                lapsi.id,
                self._get_boolean_translation(lapsi.paos_kytkin),
            ]

            if lapsi.paos_kytkin:
                paos_organisaatio = (
                    lapsi.paos_organisaatio
                    if vakasuhde.toimipaikka.vakajarjestaja != lapsi.paos_organisaatio
                    else lapsi.oma_organisaatio
                )
                vakasuhde_values.extend([paos_organisaatio.nimi, paos_organisaatio.organisaatio_oid])
            else:
                vakasuhde_values.extend([None, None])

            vakasuhde_values.extend([_get_code_translation(lahdejarjestelma_codes, lapsi.lahdejarjestelma)])

            # Vakapaatos information
            vakasuhde_values.extend(
                [
                    vakapaatos.id,
                    vakapaatos.hakemus_pvm,
                    vakapaatos.alkamis_pvm,
                    vakapaatos.paattymis_pvm,
                    _get_code_translation(jarjestamismuoto_codes, vakapaatos.jarjestamismuoto_koodi),
                    self._get_boolean_translation(vakapaatos.paivittainen_vaka_kytkin),
                    self._get_boolean_translation(vakapaatos.kokopaivainen_vaka_kytkin),
                    self._get_boolean_translation(vakapaatos.vuorohoito_kytkin),
                    vakapaatos.tuntimaara_viikossa,
                    self._get_boolean_translation(vakapaatos.tilapainen_vaka_kytkin),
                ]
            )

            # Vakasuhde information
            vakasuhde_values.extend(
                [
                    vakasuhde.id,
                    vakasuhde.alkamis_pvm,
                    vakasuhde.paattymis_pvm,
                    vakasuhde.toimipaikka.vakajarjestaja.nimi,
                    vakasuhde.toimipaikka.vakajarjestaja.organisaatio_oid,
                    vakasuhde.toimipaikka.nimi,
                    vakasuhde.toimipaikka.organisaatio_oid,
                    vakasuhde.toimipaikka.id,
                ]
            )

            self.henkilo_id_oid_set.add(
                (
                    henkilo.id,
                    henkilo.henkilo_oid,
                )
            )
            self._write_row(vakasuhde_sheet, index, vakasuhde_values)
