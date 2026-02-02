import { Component, OnDestroy, OnInit } from '@angular/core';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { VardaRaportitService } from '../../../../core/services/varda-raportit.service';
import { VardaVakajarjestajaUi } from '../../../../utilities/models/varda-vakajarjestaja-ui.model';
import { VardaExcelReportDTO } from '../../../../utilities/models/dto/varda-excel-report-dto.model';
import { VardaPaginatorParams } from '../../../../utilities/models/varda-paginator-params.model';
import { PageEvent } from '@angular/material/paginator';
import { environment } from '../../../../../environments/environment';
import { interval, Subscription } from 'rxjs';
import { Clipboard } from '@angular/cdk/clipboard';
import { VardaSnackBarService } from '../../../../core/services/varda-snackbar.service';
import { ReportStatus, ReportStatusTranslations } from '../../../../utilities/models/enums/report-status.enum';

export enum ReportType {
  VAKATIEDOT_VOIMASSA = 'VAKATIEDOT_VOIMASSA',
  MAKSUTIETO_PUUTTUU_LAPSI = 'MAKSUTIETO_PUUTTUU_LAPSI',
  PUUTTEELLISET_TOIMIPAIKKA = 'PUUTTEELLISET_TOIMIPAIKKA',
  PUUTTEELLISET_LAPSI = 'PUUTTEELLISET_LAPSI',
  PUUTTEELLISET_TYONTEKIJA = 'PUUTTEELLISET_TYONTEKIJA',
  TYONTEKIJATIEDOT_VOIMASSA = 'TYONTEKIJATIEDOT_VOIMASSA',
  TOIMIPAIKAT_VOIMASSA = 'TOIMIPAIKAT_VOIMASSA',
  VUOSIRAPORTTI = 'VUOSIRAPORTTI'
}

export enum ReportSubtype {
  ALL = 'ALL',
  VARHAISKASVATUS = 'VARHAISKASVATUS',
  HENKILOSTO = 'HENKILOSTO'
}

export const ReportTypeTranslations = {
  [ReportType.VUOSIRAPORTTI]: VirkailijaTranslations.excel_report_type_vuosiraportti,
  [ReportType.VAKATIEDOT_VOIMASSA]: VirkailijaTranslations.excel_report_type_vakatiedot_voimassa,
  [ReportType.PUUTTEELLISET_TOIMIPAIKKA]: VirkailijaTranslations.excel_report_type_puutteelliset_toimipaikka,
  [ReportType.PUUTTEELLISET_LAPSI]: VirkailijaTranslations.excel_report_type_puutteelliset_lapsi,
  [ReportType.PUUTTEELLISET_TYONTEKIJA]: VirkailijaTranslations.excel_report_type_puutteelliset_tyontekija,
  [ReportType.TYONTEKIJATIEDOT_VOIMASSA]: VirkailijaTranslations.excel_report_type_tyontekijatiedot_voimassa,
  [ReportType.TOIMIPAIKAT_VOIMASSA]: VirkailijaTranslations.excel_report_type_toimipaikat_voimassa,
  [ReportType.MAKSUTIETO_PUUTTUU_LAPSI]: VirkailijaTranslations.excel_report_type_maksutieto_puuttuu_lapsi,
};

export const ReportSubtypeTranslations = {
  [ReportSubtype.ALL]: VirkailijaTranslations.excel_report_subtype_all,
  [ReportSubtype.VARHAISKASVATUS]: VirkailijaTranslations.excel_report_subtype_varhaiskasvatus,
  [ReportSubtype.HENKILOSTO]: VirkailijaTranslations.excel_report_subtype_henkilosto
};

@Component({
    selector: 'app-varda-excel',
    templateUrl: './varda-excel.component.html',
    styleUrls: ['./varda-excel.component.css'],
    standalone: false
})
export class VardaExcelComponent implements OnInit, OnDestroy {
  i18n = VirkailijaTranslations;

  selectedVakajarjestaja: VardaVakajarjestajaUi;
  excelReportList: Array<VardaExcelReportDTO> = [];
  tableColumns = ['reportType', 'targetDate', 'toimipaikka', 'timestamp', 'status', 'password', 'download'];
  updateInterval = interval(10000);
  intervalSubscription: Subscription;

  isLoading = false;
  paginatorParams: VardaPaginatorParams = {
    page_size: 20
  };
  resultCount = 0;

  ReportStatus = ReportStatus;
  ReportType = ReportType;

  constructor(
    private vakajarjestajaService: VardaVakajarjestajaService,
    private raportitService: VardaRaportitService,
    private clipboard: Clipboard,
    private snackbarService: VardaSnackBarService
  ) { }

  ngOnInit() {
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    this.getExcelReportList();
  }

  getExcelReportList($event?: PageEvent) {
    this.intervalSubscription?.unsubscribe();

    if ($event) {
      this.paginatorParams.page_size = $event.pageSize;
    }

    this.isLoading = true;
    this.raportitService.getExcelReportList(this.selectedVakajarjestaja.id, this.paginatorParams).subscribe({
      next: result => {
        this.resultCount = result.count;
        this.excelReportList = result.results;

        // If any report has status PENDING or CREATING, refresh list every 10 seconds
        const isPendingReport = this.excelReportList.find(report => report.status === ReportStatus.PENDING ||
          report.status === ReportStatus.CREATING);
        if (isPendingReport) {
          this.intervalSubscription = this.updateInterval.subscribe(() => this.getExcelReportList());
        }
      },
      complete: () => {
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      }
    });
  }

  getReportTypeTranslationKey(reportType: string): string  {
    return ReportTypeTranslations[reportType] || reportType;
  }

  getReportSubtypeTranslationKey(reportSubtype: string): string  {
    return ReportSubtypeTranslations[reportSubtype] || reportSubtype;
  }

  getReportStatusTranslationKey(status: string): string {
    return ReportStatusTranslations[status] || status;
  }

  downloadReport(reportId: number, button: HTMLButtonElement) {
    if (button) {
      button.disabled = true;
    }

    this.raportitService.getExcelReport(reportId).subscribe({
      next: result => {
        if (environment.production && result.url.startsWith('/api/')) {
          // Frontend is run in a container but files are not in S3, we need to use same session to download the file
          this.raportitService.downloadExcelReport(`${environment.vardaAppUrl}${result.url}`).subscribe({
            next: resultData => {
              const blob = new Blob([resultData],
                {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
              const blobUrl = window.URL.createObjectURL(blob);
              window.open(blobUrl);
            },
            error: error => {
              console.error(error);
            }
          });
        } else {
          window.open(result.url);
        }
      },
      complete: () => {
        if (button) {
          button.disabled = false;
        }
      }
    });
  }

  copyToClipboard(text: string) {
    this.clipboard.copy(text);
    this.snackbarService.success(this.i18n.excel_password_copied);
  }

  ngOnDestroy() {
    this.intervalSubscription?.unsubscribe();
  }
}
