from django.http import Http404

from varda.enums.koodistot import Koodistot
from varda.enums.translation import Translation as T
from varda.excel_export.base import BaseExcelReportGenerator
from varda.excel_export.utils import _get_code_translation, _get_dates_for_model_and_id
from varda.misc import TemporaryObject, decrypt_henkilotunnus
from varda.models import Lapsi, Toimipaikka, Tyontekija

PUUTTEELLISET_TOIMIPAIKKA_HEADERS = (
    T.EXCEL_TOIMIPAIKKA_NIMI,
    T.EXCEL_TOIMIPAIKKA_OID,
    T.EXCEL_TOIMIPAIKKA_ID,
    T.EXCEL_LAHDEJARJESTELMA,
    T.EXCEL_ERROR,
    T.EXCEL_TIETOSISALTO,
    T.EXCEL_OBJECT_ID,
    T.EXCEL_VOIMASSAOLO,
)

PUUTTEELLISET_LAPSI_HEADERS = (
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
    T.EXCEL_ERROR,
    T.EXCEL_TIETOSISALTO,
    T.EXCEL_OBJECT_ID,
    T.EXCEL_VOIMASSAOLO,
)

PUUTTEELLISET_TYONTEKIJA_HEADERS = (
    T.EXCEL_OPPIJANUMERO,
    T.EXCEL_ETUNIMET,
    T.EXCEL_SUKUNIMI,
    T.EXCEL_HETU,
    T.EXCEL_TURVAKIELTO,
    T.EXCEL_TYONTEKIJA_ID,
    T.EXCEL_LAHDEJARJESTELMA,
    T.EXCEL_ERROR,
    T.EXCEL_TIETOSISALTO,
    T.EXCEL_OBJECT_ID,
    T.EXCEL_VOIMASSAOLO,
)


class PuutteellisetReportGeneratorBase(BaseExcelReportGenerator):
    viewset_class = None
    headers = ()
    error_koodisto = None
    lahdejarjestelma_koodisto = None

    def _get_instance_values(self, instance_data):
        raise NotImplementedError

    def _create_excel_report(self):
        viewset = self.viewset_class()

        worksheet = self._add_worksheet(T.EXCEL_PUUTTEELLISET_TIEDOT)
        self._write_headers(worksheet, self.headers)

        # Initialize ViewSet by setting properties
        viewset.vakajarjestaja_id = self.organisaatio_id
        viewset.vakajarjestaja_oid = self.report.organisaatio.organisaatio_oid
        viewset.format_kwarg = None
        temp_request_object = TemporaryObject()
        temp_request_object.user = self.report.user
        temp_request_object.query_params = {}
        viewset.request = temp_request_object

        try:
            # Verify permissions and set internal properties
            viewset.verify_permissions()
        except Http404:
            # No permissions
            return None

        self.error_koodisto = self._get_koodisto_with_translations(Koodistot.virhe_koodit.value)
        self.lahdejarjestelma_koodisto = self._get_koodisto_with_translations(Koodistot.lahdejarjestelma_koodit.value)

        queryset = viewset.get_queryset()
        serializer_data = viewset.get_serializer(queryset, many=True).data

        index = 1
        for instance_data in serializer_data:
            instance_values = self._get_instance_values(instance_data)
            for error in instance_data["errors"]:
                for model_id in error["model_id_list"]:
                    error_values = [
                        _get_code_translation(self.error_koodisto, error["error_code"]),
                        error["model_name"],
                        model_id,
                        _get_dates_for_model_and_id(error["model_name"], model_id),
                    ]
                    self._write_row(worksheet, index, instance_values + error_values)
                    index += 1


class PuutteellisetToimipaikkaReportGenerator(PuutteellisetReportGeneratorBase):
    filename_key = T.EXCEL_FILENAME_PUUTTEELLISET_TOIMIPAIKKA
    headers = PUUTTEELLISET_TOIMIPAIKKA_HEADERS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from varda.viewsets_reporting import ErrorReportToimipaikatViewSet  # Import locally to avoid circular reference

        self.viewset_class = ErrorReportToimipaikatViewSet

    def _get_instance_values(self, instance_data):
        toimipaikka = Toimipaikka.objects.get(id=instance_data["toimipaikka_id"])
        return [
            toimipaikka.nimi,
            toimipaikka.organisaatio_oid,
            toimipaikka.id,
            _get_code_translation(self.lahdejarjestelma_koodisto, toimipaikka.lahdejarjestelma),
        ]


class PuutteellisetLapsiReportGenerator(PuutteellisetReportGeneratorBase):
    filename_key = T.EXCEL_FILENAME_PUUTTEELLISET_LAPSI
    headers = PUUTTEELLISET_LAPSI_HEADERS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from varda.viewsets_reporting import ErrorReportLapsetViewSet  # Import locally to avoid circular reference

        self.viewset_class = ErrorReportLapsetViewSet

    def _get_instance_values(self, instance_data):
        lapsi = Lapsi.objects.get(id=instance_data["lapsi_id"])
        henkilo = lapsi.henkilo
        values = [
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
            values.extend([paos_organisaatio.nimi, paos_organisaatio.organisaatio_oid])
        else:
            values.extend([None, None])

        values.append(_get_code_translation(self.lahdejarjestelma_koodisto, lapsi.lahdejarjestelma))
        return values


class PuutteellisetTyontekijaReportGenerator(PuutteellisetReportGeneratorBase):
    filename_key = T.EXCEL_FILENAME_PUUTTEELLISET_TYONTEKIJA
    headers = PUUTTEELLISET_TYONTEKIJA_HEADERS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from varda.viewsets_reporting import ErrorReportTyontekijatViewSet  # Import locally to avoid circular reference

        self.viewset_class = ErrorReportTyontekijatViewSet

    def _get_instance_values(self, instance_data):
        tyontekija = Tyontekija.objects.get(id=instance_data["tyontekija_id"])
        henkilo = tyontekija.henkilo
        return [
            henkilo.henkilo_oid,
            henkilo.etunimet,
            henkilo.sukunimi,
            decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id, raise_error=False),
            self._get_boolean_translation(henkilo.turvakielto),
            tyontekija.id,
            _get_code_translation(self.lahdejarjestelma_koodisto, tyontekija.lahdejarjestelma),
        ]
