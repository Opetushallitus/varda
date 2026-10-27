from varda.excel_export.constants import ExcelReportType
from varda.excel_export.reports.maksutieto_puuttuu import MaksutietoPuuttuuLapsiReportGenerator
from varda.excel_export.reports.puutteelliset import (
    PuutteellisetLapsiReportGenerator,
    PuutteellisetToimipaikkaReportGenerator,
    PuutteellisetTyontekijaReportGenerator,
)
from varda.excel_export.reports.toimipaikat import ToimipaikatVoimassaReportGenerator
from varda.excel_export.reports.tyontekijatiedot import (
    TyontekijatiedotMaaraaikaisetVoimassaReportGenerator,
    TyontekijatiedotVoimassaReportGenerator,
)
from varda.excel_export.reports.vakatiedot import (
    VakatiedotVoimassa8yOlderReportGenerator,
    VakatiedotVoimassaReportGenerator,
)
from varda.excel_export.reports.vuosiraportti import VuosiraporttiReportGenerator

REPORT_GENERATORS = {
    ExcelReportType.VUOSIRAPORTTI.value: VuosiraporttiReportGenerator,
    ExcelReportType.VAKATIEDOT_VOIMASSA.value: VakatiedotVoimassaReportGenerator,
    ExcelReportType.VAKATIEDOT_VOIMASSA_8Y_OLDER.value: VakatiedotVoimassa8yOlderReportGenerator,
    ExcelReportType.PUUTTEELLISET_TOIMIPAIKKA.value: PuutteellisetToimipaikkaReportGenerator,
    ExcelReportType.PUUTTEELLISET_LAPSI.value: PuutteellisetLapsiReportGenerator,
    ExcelReportType.PUUTTEELLISET_TYONTEKIJA.value: PuutteellisetTyontekijaReportGenerator,
    ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value: TyontekijatiedotVoimassaReportGenerator,
    ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value: TyontekijatiedotMaaraaikaisetVoimassaReportGenerator,
    ExcelReportType.TOIMIPAIKAT_VOIMASSA.value: ToimipaikatVoimassaReportGenerator,
    ExcelReportType.MAKSUTIETO_PUUTTUU_LAPSI.value: MaksutietoPuuttuuLapsiReportGenerator,
}
