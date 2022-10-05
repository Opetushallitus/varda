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
import { VardaDateService, KoodistoEnum } from 'varda-shared';
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
  KoodistoEnum = KoodistoEnum;

  currentVakajarjestaja: VardaVakajarjestajaUi;
  isOPHUser = false;
  today = new Date();

  newYearlyReport: VardaYearlyReportPostDTO;
  poimintaPvm: Moment = null;
  yearlyReport: VardaYearlyReportDTO;
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

  getEntries(obj: object) {
    return Object.entries(obj);
  }

  ngOnDestroy() {
    this.intervalSubscription?.unsubscribe();
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
