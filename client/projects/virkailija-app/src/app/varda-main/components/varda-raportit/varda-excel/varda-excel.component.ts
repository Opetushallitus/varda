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

export enum ReportType {
  VAKATIEDOT_VOIMASSA = 'VAKATIEDOT_VOIMASSA',
  PUUTTEELLISET_TOIMIPAIKKA = 'PUUTTEELLISET_TOIMIPAIKKA',
  PUUTTEELLISET_LAPSI = 'PUUTTEELLISET_LAPSI',
  PUUTTEELLISET_TYONTEKIJA = 'PUUTTEELLISET_TYONTEKIJA',
  TYONTEKIJATIEDOT_VOIMASSA = 'TYONTEKIJATIEDOT_VOIMASSA',
  TAYDENNYSKOULUTUSTIEDOT = 'TAYDENNYSKOULUTUSTIEDOT',
  TOIMIPAIKAT_VOIMASSA = 'TOIMIPAIKAT_VOIMASSA'
}

export const ReportTypeTranslations = {
  [ReportType.VAKATIEDOT_VOIMASSA]: VirkailijaTranslations.excel_report_type_vakatiedot_voimassa,
  [ReportType.PUUTTEELLISET_TOIMIPAIKKA]: VirkailijaTranslations.excel_report_type_puutteelliset_toimipaikka,
  [ReportType.PUUTTEELLISET_LAPSI]: VirkailijaTranslations.excel_report_type_puutteelliset_lapsi,
  [ReportType.PUUTTEELLISET_TYONTEKIJA]: VirkailijaTranslations.excel_report_type_puutteelliset_tyontekija,
  [ReportType.TYONTEKIJATIEDOT_VOIMASSA]: VirkailijaTranslations.excel_report_type_tyontekijatiedot_voimassa,
  [ReportType.TAYDENNYSKOULUTUSTIEDOT]: VirkailijaTranslations.excel_report_type_taydennyskoulutustiedot,
  [ReportType.TOIMIPAIKAT_VOIMASSA]: VirkailijaTranslations.excel_report_type_toimipaikat_voimassa
};

enum ReportStatus {
  PENDING = 'PENDING',
  CREATING = 'CREATING',
  FINISHED = 'FINISHED',
  FAILED = 'FAILED'
}

const ReportStatusTranslations = {
  [ReportStatus.PENDING]: VirkailijaTranslations.excel_status_pending,
  [ReportStatus.CREATING]: VirkailijaTranslations.excel_status_creating,
  [ReportStatus.FINISHED]: VirkailijaTranslations.excel_status_finished,
  [ReportStatus.FAILED]: VirkailijaTranslations.excel_status_failed,
};

@Component({
  selector: 'app-varda-excel',
  templateUrl: './varda-excel.component.html',
  styleUrls: ['./varda-excel.component.css']
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
    page: 1,
    page_size: 20
  };
  resultCount = 0;

  ReportStatus = ReportStatus;

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
      this.paginatorParams.page = $event.pageIndex + 1;
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
