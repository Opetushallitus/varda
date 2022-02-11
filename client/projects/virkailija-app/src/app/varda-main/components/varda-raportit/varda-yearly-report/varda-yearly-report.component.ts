import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaUi } from '../../../../utilities/models/varda-vakajarjestaja-ui.model';
import { interval, Observable, Subscription } from 'rxjs';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { VardaRaportitService } from '../../../../core/services/varda-raportit.service';
import { VardaSnackBarService } from '../../../../core/services/varda-snackbar.service';
import { ReportStatus, ReportStatusTranslations } from '../../../../utilities/models/enums/report-status.enum';
import {
  VardaYearlyReportDTO,
  VardaYearlyReportPostDTO
} from '../../../../utilities/models/dto/varda-yearly-report-dto.model';
import moment, { Moment } from 'moment';
import { VardaDateService } from 'varda-shared';
import { AuthService } from '../../../../core/auth/auth.service';
import { ErrorTree, VardaErrorMessageService } from '../../../../core/services/varda-error-message.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaAutocompleteSelectorComponent } from '../../../../shared/components/varda-autocomplete-selector/varda-autocomplete-selector.component';
import { NgModel } from '@angular/forms';

@Component({
  selector: 'app-varda-yearly-report',
  templateUrl: './varda-yearly-report.component.html',
  styleUrls: ['./varda-yearly-report.component.css']
})
export class VardaYearlyReportComponent implements OnInit, OnDestroy {
  @ViewChild('organizationSelector') organizationSelector: VardaAutocompleteSelectorComponent<VardaVakajarjestajaUi>;
  @ViewChild('datePicker') datePicker: NgModel;

  i18n = VirkailijaTranslations;

  currentVakajarjestaja: VardaVakajarjestajaUi;
  isOPHUser = false;
  today = new Date();

  newYearlyReport: VardaYearlyReportPostDTO;
  poimintaPvm: Moment = null;
  yearlyReport: VardaYearlyReportDTO;
  datasourceAll: Array<{name: string; value: number | boolean}> = [];
  datasourceOwn: Array<{name: string; value: number | boolean}> = [];
  datasourcePaos: Array<{name: string; value: number | boolean}> = [];
  displayedColumns = ['name', 'value'];
  updateInterval = interval(10000);
  yearOptions: Array<number> = [];
  organizationOptions: Array<VardaVakajarjestajaUi> = [];
  selectedVakajarjestaja?: VardaVakajarjestajaUi;

  intervalSubscription: Subscription;
  isLoading = false;
  subscriptions: Array<Subscription> = [];

  ReportStatus = ReportStatus;

  errors: Observable<Array<ErrorTree>>;
  private errorService: VardaErrorMessageService;

  constructor(
    private vakajarjestajaService: VardaVakajarjestajaService,
    private raportitService: VardaRaportitService,
    private dateService: VardaDateService,
    private authService: AuthService,
    private snackbarService: VardaSnackBarService,
    private translateService: TranslateService
  ) { }

  ngOnInit() {
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.errors = this.errorService.initErrorList();

    this.isOPHUser = this.authService.isOPHUser || this.authService.isAdminUser;

    this.currentVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    this.selectedVakajarjestaja = this.isOPHUser ? null : this.currentVakajarjestaja;
    const currentYear = moment().year();
    this.newYearlyReport = {
      vakajarjestaja_input: this.isOPHUser ? 'all' : this.currentVakajarjestaja.id.toString(),
      tilastovuosi: currentYear - 1,
      poiminta_pvm: this.dateService.momentToISODateTime(this.poimintaPvm)
    };

    this.subscriptions = [
      this.vakajarjestajaService.getVakajarjestajat().subscribe(organizations => {
        this.organizationOptions = organizations;
      })
    ];

    const startYear = currentYear - 5;
    for (let i = startYear; i < currentYear; i++) {
      if (i > 2019) {
        // Cannot create report before 2019
        this.yearOptions.push(i);
      }
    }
  }

  postYearlyReport() {
    this.intervalSubscription?.unsubscribe();
    if (!this.yearlyReport) {
      // Creating new report
      if ((this.poimintaPvm && !this.poimintaPvm.isValid()) || !this.datePicker?.valid || this.organizationSelector.isOptionInvalid()) {
        return;
      }
      this.newYearlyReport.poiminta_pvm = this.dateService.momentToISODateTime(this.poimintaPvm?.set({hour: 6, minute: 0, second: 0, millisecond: 0}));
      this.newYearlyReport.vakajarjestaja_input = this.selectedVakajarjestaja ? this.selectedVakajarjestaja.id.toString() : 'all';
    }

    this.isLoading = true;
    this.raportitService.postYearlyReport(this.newYearlyReport).subscribe({
      next: result => {
        this.isLoading = false;
        this.yearlyReport = result;
        if (this.yearlyReport.status === ReportStatus.PENDING || this.yearlyReport.status === ReportStatus.CREATING) {
          // If report has status PENDING or CREATING, refresh every 10 seconds
          this.intervalSubscription = this.updateInterval.subscribe(() => this.postYearlyReport());
        } else if (this.yearlyReport.status === ReportStatus.FINISHED) {
          this.datasourceAll = [
            [this.i18n.yearly_report_result_vakajarjestaja_count, result.vakajarjestaja_count],
            [this.i18n.yearly_report_result_vakajarjestaja_is_active, result.vakajarjestaja_is_active],
            [this.i18n.yearly_report_result_toimipaikka_count, result.toimipaikka_count],
            [this.i18n.yearly_report_result_toimintapainotus_count, result.toimintapainotus_count],
            [this.i18n.yearly_report_result_kielipainotus_count, result.kielipainotus_count],
            [this.i18n.yearly_report_result_yhteensa_henkilo_count, result.yhteensa_henkilo_count],
            [this.i18n.yearly_report_result_yhteensa_lapsi_count, result.yhteensa_lapsi_count],
            [this.i18n.yearly_report_result_yhteensa_varhaiskasvatussuhde_count, result.yhteensa_varhaiskasvatussuhde_count],
            [this.i18n.yearly_report_result_yhteensa_varhaiskasvatuspaatos_count, result.yhteensa_varhaiskasvatuspaatos_count],
            [this.i18n.yearly_report_result_yhteensa_vuorohoito_count, result.yhteensa_vuorohoito_count],
            [this.i18n.yearly_report_result_yhteensa_maksutieto_count, result.yhteensa_maksutieto_count],
            [this.i18n.yearly_report_result_yhteensa_maksutieto_mp01_count, result.yhteensa_maksutieto_mp01_count],
            [this.i18n.yearly_report_result_yhteensa_maksutieto_mp02_count, result.yhteensa_maksutieto_mp02_count],
            [this.i18n.yearly_report_result_yhteensa_maksutieto_mp03_count, result.yhteensa_maksutieto_mp03_count]
          ].map(item => ({name: item[0] as string, value: item[1] as number | boolean}));

          this.datasourceOwn = [
            [this.i18n.yearly_report_result_oma_henkilo_count, result.oma_henkilo_count],
            [this.i18n.yearly_report_result_oma_lapsi_count, result.oma_lapsi_count],
            [this.i18n.yearly_report_result_oma_varhaiskasvatussuhde_count, result.oma_varhaiskasvatussuhde_count],
            [this.i18n.yearly_report_result_oma_varhaiskasvatuspaatos_count, result.oma_varhaiskasvatuspaatos_count],
            [this.i18n.yearly_report_result_oma_vuorohoito_count, result.oma_vuorohoito_count],
            [this.i18n.yearly_report_result_oma_maksutieto_count, result.oma_maksutieto_count],
            [this.i18n.yearly_report_result_oma_maksutieto_mp01_count, result.oma_maksutieto_mp01_count],
            [this.i18n.yearly_report_result_oma_maksutieto_mp02_count, result.oma_maksutieto_mp02_count],
            [this.i18n.yearly_report_result_oma_maksutieto_mp03_count, result.oma_maksutieto_mp03_count]
          ].map(item => ({name: item[0] as string, value: item[1] as number | boolean}));

          this.datasourcePaos = [
            [this.i18n.yearly_report_result_paos_henkilo_count, result.paos_henkilo_count],
            [this.i18n.yearly_report_result_paos_lapsi_count, result.paos_lapsi_count],
            [this.i18n.yearly_report_result_paos_varhaiskasvatussuhde_count, result.paos_varhaiskasvatussuhde_count],
            [this.i18n.yearly_report_result_paos_varhaiskasvatuspaatos_count, result.paos_varhaiskasvatuspaatos_count],
            [this.i18n.yearly_report_result_paos_vuorohoito_count, result.paos_vuorohoito_count],
            [this.i18n.yearly_report_result_paos_maksutieto_count, result.paos_maksutieto_count],
            [this.i18n.yearly_report_result_paos_maksutieto_mp01_count, result.paos_maksutieto_mp01_count],
            [this.i18n.yearly_report_result_paos_maksutieto_mp02_count, result.paos_maksutieto_mp02_count],
            [this.i18n.yearly_report_result_paos_maksutieto_mp03_count, result.paos_maksutieto_mp03_count]
          ].map(item => ({name: item[0] as string, value: item[1] as number | boolean}));
        }
      }, error: error => {
        this.errorService.handleError(error, this.snackbarService);
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      }
    });
  }

  getUiDateTime(dateTime: string) {
    return this.dateService.apiDateTimeToUiDate(dateTime);
  }

  getReportStatusTranslationKey(status: string): string {
    return ReportStatusTranslations[status] || status;
  }

  cancel() {
    this.intervalSubscription?.unsubscribe();
    this.yearlyReport = null;
  }

  ngOnDestroy() {
    this.intervalSubscription?.unsubscribe();
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
