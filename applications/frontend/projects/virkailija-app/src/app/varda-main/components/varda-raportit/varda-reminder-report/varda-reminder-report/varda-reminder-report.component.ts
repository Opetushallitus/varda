import {Component, OnInit} from '@angular/core';
import { BehaviorSubject, Observable} from 'rxjs';
import { KoodistoEnum } from 'varda-shared';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import {ErrorTree, VardaErrorMessageService} from "../../../../../core/services/varda-error-message.service";
import {VardaRaportitService} from "../../../../../core/services/varda-raportit.service";
import {VirkailijaTranslations} from "../../../../../../assets/i18n/virkailija-translations.enum";
import {FormBuilder, FormGroup, Validators} from "@angular/forms";

@Component({
    selector: 'app-varda-reminder-report',
    templateUrl: './varda-reminder-report.component.html',
    styleUrl: './varda-reminder-report.component.css',
    standalone: false
})
export class VardaReminderReportComponent implements OnInit {
  i18n = VirkailijaTranslations;
  isLoading = new BehaviorSubject<boolean>(false);
  errors: Observable<Array<ErrorTree>>;
  koodistoEnum = KoodistoEnum;
  startDate: string;
  endDate: string;
  reportForm: FormGroup;
  noReport = false;

  private errorService: VardaErrorMessageService;

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private raportitService: VardaRaportitService,
    private translateService: TranslateService,
  ) {
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.errors = this.errorService.initErrorList();
  }

  ngOnInit() {
    this.initForm();
  }

  initForm() {
    this.reportForm = this.fb.group({
      startDate: ['', Validators.required],
      endDate: ['', Validators.required]
    });
  }

  downloadFile(blob: Blob) {
    this.isLoading.next(true);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'output.csv';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
  }

  downloadCsv() {
    const startDateValue = this.reportForm.get('startDate').value;
    const endDateValue = this.reportForm.get('endDate').value;

    const startDate = startDateValue.toFormat('yyyy-MM-dd');
    const endDate = endDateValue.toFormat('yyyy-MM-dd');

    // Use the values of startDate and endDate in the API call
    this.raportitService.getReminderReport(startDate, endDate).subscribe({
      next: blob => {
        if (blob) {
          this.downloadFile(blob);
          this.noReport = false;
        } else {
          this.noReport = true;
        }

      },
      error: err => {
        this.errorService.handleError(err);
      }
    }).add(() => setTimeout(() => this.isLoading.next(false), 1000));
  }
}
