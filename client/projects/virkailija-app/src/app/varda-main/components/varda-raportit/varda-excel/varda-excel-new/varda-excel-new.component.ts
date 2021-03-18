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
import { VardaDateService } from '../../../../services/varda-date.service';

const TooltipTranslations = {
  [ReportType.VAKATIEDOT_VOIMASSA]: VirkailijaTranslations.excel_report_type_description_vakatiedot_voimassa
};

@Component({
  selector: 'app-varda-excel-new',
  templateUrl: './varda-excel-new.component.html',
  styleUrls: ['./varda-excel-new.component.css']
})
export class VardaExcelNewComponent implements OnInit {
  @ViewChild('toimipaikkaSelector') toimipaikkaSelector: VardaAutocompleteSelectorComponent<VardaToimipaikkaMinimalDto>;
  private errorService: VardaErrorMessageService;
  errors: Observable<Array<ErrorTree>>;

  i18n = VirkailijaTranslations;

  selectedVakajarjestaja: VardaVakajarjestajaUi;

  toimipaikkaList: Array<VardaToimipaikkaMinimalDto> = [];
  henkilostoToimipaikkaList: Array<VardaToimipaikkaMinimalDto> = [];
  toimipaikkaOptions: Array<VardaToimipaikkaMinimalDto> = [];

  reportTypeOptions: Array<Array<string>>;
  ReportType = ReportType;

  newReport: VardaExcelReportPostDTO = {
    report_type: ReportType.VAKATIEDOT_VOIMASSA,
    language: 'FI',
    vakajarjestaja_oid: null,
    toimipaikka_oid: null,
    target_date: null,
  };

  targetDate = moment();

  vakajarjestajaLevel = true;
  selectedToimipaikka: VardaToimipaikkaMinimalDto = null;

  isLoading = false;

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

    this.reportTypeOptions = Object.entries(ReportTypeTranslations).map(value => {
      return [value[0], value[1]];
    });
  }

  create() {
    if (!this.vakajarjestajaLevel) {
      if (this.selectedToimipaikka && !this.toimipaikkaSelector.isOptionInvalid()) {
        this.newReport.toimipaikka_oid = this.selectedToimipaikka.organisaatio_oid;
      } else {
        this.newReport.toimipaikka_oid = null;
        this.toimipaikkaSelector.setInvalid();
        return;
      }
    }

    if (this.newReport.report_type === ReportType.VAKATIEDOT_VOIMASSA) {
      if (!this.targetDate?.isValid()) {
        return;
      } else {
        this.newReport.target_date = this.dateService.momentToVardaDate(this.targetDate);
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
    console.log('TODO: Update toimipaikat to reflect if report is for vakatiedot or henkilostotiedot');
  }

  getTooltipTranslation(reportType: string) {
    return TooltipTranslations[reportType];
  }
}
