import { Component, OnInit, ViewChild } from '@angular/core';
import { VirkailijaTranslations } from '../../../../../../assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaService } from '../../../../../core/services/varda-vakajarjestaja.service';
import { VardaRaportitService } from '../../../../../core/services/varda-raportit.service';
import { VardaVakajarjestajaUi } from '../../../../../utilities/models/varda-vakajarjestaja-ui.model';
import { VardaToimipaikkaMinimalDto } from '../../../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { ViewAccess } from '../../../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../../../core/auth/auth.service';
import { VardaExcelReportPostDTO } from '../../../../../utilities/models/dto/varda-excel-report-dto.model';
import { ReportType, ReportTypeTranslations } from '../varda-excel.component';
import { VardaAutocompleteSelectorComponent } from '../../../../../shared/components/varda-autocomplete-selector/varda-autocomplete-selector.component';
import { VardaSnackBarService } from '../../../../../core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { ErrorTree, VardaErrorMessageService } from '../../../../../core/services/varda-error-message.service';
import { Observable } from 'rxjs';
import { ActivatedRoute, Router } from '@angular/router';
import * as moment from 'moment';
import { VardaDateService } from 'varda-shared';

const TooltipTranslations = {
  [ReportType.VAKATIEDOT_VOIMASSA]: VirkailijaTranslations.excel_report_type_description_vakatiedot_voimassa,
  [ReportType.PUUTTEELLISET_TOIMIPAIKKA]: VirkailijaTranslations.excel_report_type_description_puutteelliset_toimipaikka,
  [ReportType.PUUTTEELLISET_LAPSI]: VirkailijaTranslations.excel_report_type_description_puutteelliset_lapsi,
  [ReportType.PUUTTEELLISET_TYONTEKIJA]: VirkailijaTranslations.excel_report_type_description_puutteelliset_tyontekija,
  [ReportType.TYONTEKIJATIEDOT_VOIMASSA]: VirkailijaTranslations.excel_report_type_description_tyontekijatiedot_voimassa,
  [ReportType.TAYDENNYSKOULUTUSTIEDOT]: VirkailijaTranslations.excel_report_type_description_taydennyskoulutustiedot
};

@Component({
  selector: 'app-varda-excel-new',
  templateUrl: './varda-excel-new.component.html',
  styleUrls: ['./varda-excel-new.component.css']
})
export class VardaExcelNewComponent implements OnInit {
  @ViewChild('toimipaikkaSelector') toimipaikkaSelector: VardaAutocompleteSelectorComponent<VardaToimipaikkaMinimalDto>;
  errors: Observable<Array<ErrorTree>>;

  i18n = VirkailijaTranslations;

  selectedVakajarjestaja: VardaVakajarjestajaUi;

  toimipaikkaList: Array<VardaToimipaikkaMinimalDto> = [];
  henkilostoToimipaikkaList: Array<VardaToimipaikkaMinimalDto> = [];
  toimipaikkaOptions: Array<VardaToimipaikkaMinimalDto> = [];

  reportTypeOptions: Array<Array<string>>;

  newReport: VardaExcelReportPostDTO = {
    report_type: ReportType.VAKATIEDOT_VOIMASSA,
    language: 'FI',
    vakajarjestaja_oid: null,
    toimipaikka_oid: null,
    target_date: null,
    target_date_start: null,
    target_date_end: null
  };

  targetDate = moment();
  targetDateStart = moment();
  targetDateEnd = moment();

  vakajarjestajaLevel = true;
  selectedToimipaikka: VardaToimipaikkaMinimalDto = null;

  toimipaikkaSelectorReports = [ReportType.VAKATIEDOT_VOIMASSA.toString(), ReportType.TYONTEKIJATIEDOT_VOIMASSA.toString(),
    ReportType.TAYDENNYSKOULUTUSTIEDOT.toString()];
  dateSelectorReports = [ReportType.VAKATIEDOT_VOIMASSA.toString(), ReportType.TYONTEKIJATIEDOT_VOIMASSA.toString()];
  dateRangeSelectorReports = [ReportType.TAYDENNYSKOULUTUSTIEDOT.toString()];

  isLoading = false;
  private errorService: VardaErrorMessageService;

  constructor(
    private vakajarjestajaService: VardaVakajarjestajaService,
    private raportitService: VardaRaportitService,
    private authService: AuthService,
    private snackBarService: VardaSnackBarService,
    private translateService: TranslateService,
    private router: Router,
    private activatedRoute: ActivatedRoute,
    private dateService: VardaDateService,
  ) { }

  ngOnInit() {
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.errors = this.errorService.initErrorList();

    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();

    this.toimipaikkaList = this.vakajarjestajaService.getFilteredToimipaikat().katselijaToimipaikat;
    this.henkilostoToimipaikkaList = this.authService.getAuthorizedToimipaikat(this.toimipaikkaList, ViewAccess.henkilostotiedot);
    this.toimipaikkaOptions = this.toimipaikkaList;

    this.newReport.vakajarjestaja_oid = this.selectedVakajarjestaja.organisaatio_oid;

    this.reportTypeOptions = Object.entries(ReportTypeTranslations).map(value => [value[0], value[1]]);

    this.newReport.language = this.translateService.currentLang;
  }

  create() {
    if (!this.vakajarjestajaLevel && this.toimipaikkaSelectorReports.includes(this.newReport.report_type)) {
      if (this.selectedToimipaikka && !this.toimipaikkaSelector.isOptionInvalid()) {
        this.newReport.toimipaikka_oid = this.selectedToimipaikka.organisaatio_oid;
      } else {
        this.newReport.toimipaikka_oid = null;
        this.toimipaikkaSelector.setInvalid();
        return;
      }
    }

    if (this.dateSelectorReports.includes(this.newReport.report_type)) {
      if (!this.targetDate?.isValid()) {
        return;
      } else {
        this.newReport.target_date = this.dateService.momentToVardaDate(this.targetDate);
      }
    }

    if (this.dateRangeSelectorReports.includes(this.newReport.report_type)) {
      if (!this.targetDateStart?.isValid() || !this.targetDateEnd?.isValid()) {
        return;
      } else {
        this.newReport.target_date_start = this.dateService.momentToVardaDate(this.targetDateStart);
        this.newReport.target_date_end = this.dateService.momentToVardaDate(this.targetDateEnd);
      }
    }

    this.isLoading = true;
    this.raportitService.postExcelReport(this.newReport).subscribe({
      next: result => {
        this.router.navigate(['../'], {relativeTo: this.activatedRoute});
      }, error: error => {
        this.errorService.handleError(error, this.snackBarService);
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      }
    });
  }

  updateToimipaikat() {
    this.vakajarjestajaLevel = true;
    this.selectedToimipaikka = null;
    this.newReport.toimipaikka_oid = null;
    switch (this.newReport.report_type) {
      case ReportType.VAKATIEDOT_VOIMASSA:
        this.toimipaikkaOptions = this.toimipaikkaList;
        break;
      case ReportType.TYONTEKIJATIEDOT_VOIMASSA:
      case ReportType.TAYDENNYSKOULUTUSTIEDOT:
        this.toimipaikkaOptions = this.henkilostoToimipaikkaList;
        break;
      default:
        break;
    }
  }

  getTooltipTranslation(reportType: string) {
    return TooltipTranslations[reportType];
  }
}
