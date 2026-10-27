from django.db.models import Count, Exists, OuterRef, Q

from varda.enums.translation import Translation as T
from varda.excel_export.base import BaseExcelReportGenerator
from varda.misc import decrypt_henkilotunnus
from varda.models import Lapsi, Maksutieto, Varhaiskasvatuspaatos

MAKSUTIETO_PUUTTUU_LAPSI_HEADERS = (
    T.EXCEL_VAKATOIMIJA_NIMI,
    T.EXCEL_OPPIJANUMERO,
    T.EXCEL_ETUNIMET,
    T.EXCEL_SUKUNIMI,
    T.EXCEL_HETU,
    T.EXCEL_LAPSI_ID,
    T.EXCEL_HUOLTAJUUSSUHTEET_VOIMASSA,
)


class MaksutietoPuuttuuLapsiReportGenerator(BaseExcelReportGenerator):
    filename_key = T.EXCEL_FILENAME_MAKSUTIETO_PUUTTUU_LAPSI

    def _create_excel_report(self):
        target_date = self.report.target_date

        # Overlapping Maksutieto
        overlapping_maksutieto_subquery = Maksutieto.objects.filter(
            huoltajuussuhteet__lapsi=OuterRef("id"), alkamis_pvm__lte=target_date
        ).filter(Q(paattymis_pvm__gte=target_date) | Q(paattymis_pvm__isnull=True))

        # Active Varhaiskasvatuspaatos and Varhaiskasvatussuhde subquery
        active_vakasuhde_subquery = (
            Varhaiskasvatuspaatos.objects.filter(lapsi=OuterRef("id"), alkamis_pvm__lte=target_date)
            .filter(
                Q(paattymis_pvm__gte=target_date) | Q(paattymis_pvm__isnull=True),
                varhaiskasvatussuhteet__alkamis_pvm__lte=target_date,
            )
            .filter(
                Q(varhaiskasvatussuhteet__paattymis_pvm__gte=target_date) | Q(varhaiskasvatussuhteet__paattymis_pvm__isnull=True)
            )
        )

        lapsi_qs = (
            Lapsi.objects.annotate(
                has_maksutieto_overlap=Exists(overlapping_maksutieto_subquery),
                has_active_vakasuhde=Exists(active_vakasuhde_subquery),
                active_huoltajuussuhteet_count=Count("huoltajuussuhteet", filter=Q(huoltajuussuhteet__voimassa_kytkin=True)),
            )
            .filter(
                has_maksutieto_overlap=False,
                has_active_vakasuhde=True,
                **({"vakatoimija": self.report.organisaatio} if self.report.organisaatio else {}),
            )
            .values(
                "henkilo__id",
                "henkilo__henkilo_oid",
                "henkilo__etunimet",
                "henkilo__sukunimi",
                "henkilo__henkilotunnus",
                "id",
                "active_huoltajuussuhteet_count",
                "vakatoimija__nimi",
            )
            .distinct()
            .order_by("vakatoimija__nimi", "henkilo__henkilo_oid")
        )

        maksutieto_puuttuu_sheet = self._add_worksheet(T.EXCEL_MAKSUTIETO_PUUTTUU_LAPSI)
        self._write_headers(maksutieto_puuttuu_sheet, MAKSUTIETO_PUUTTUU_LAPSI_HEADERS)
        for index, lapsi in enumerate(lapsi_qs.iterator(chunk_size=500), 1):
            lapsi_values = [
                lapsi["vakatoimija__nimi"],
                lapsi["henkilo__henkilo_oid"],
                lapsi["henkilo__etunimet"],
                lapsi["henkilo__sukunimi"],
                decrypt_henkilotunnus(lapsi["henkilo__henkilotunnus"], henkilo_id=lapsi["henkilo__id"], raise_error=False),
                lapsi["id"],
                lapsi["active_huoltajuussuhteet_count"],
            ]

            self._write_row(maksutieto_puuttuu_sheet, index, lapsi_values)
