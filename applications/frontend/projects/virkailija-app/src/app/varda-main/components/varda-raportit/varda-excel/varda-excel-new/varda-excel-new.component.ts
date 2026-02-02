import { Component, OnInit, ViewChild } from '@angular/core';
import { VirkailijaTranslations } from '../../../../../../assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaService } from '../../../../../core/services/varda-vakajarjestaja.service';
import { VardaRaportitService } from '../../../../../core/services/varda-raportit.service';
import { VardaToimipaikkaMinimalDto } from '../../../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { ViewAccess } from '../../../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../../../core/auth/auth.service';
import { VardaExcelReportPostDTO } from '../../../../../utilities/models/dto/varda-excel-report-dto.model';
import { ReportSubtype, ReportSubtypeTranslations, ReportType, ReportTypeTranslations } from '../varda-excel.component';
import { VardaAutocompleteSelectorComponent } from '../../../../../shared/components/varda-autocomplete-selector/varda-autocomplete-selector.component';
import { VardaSnackBarService } from '../../../../../core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { ErrorTree, VardaErrorMessageService } from '../../../../../core/services/varda-error-message.service';
import { Observable } from 'rxjs';
import { ActivatedRoute, Router } from '@angular/router';
import { DateTime } from 'luxon';
import { VardaDateService } from 'varda-shared';
import { FormControl, FormGroup } from '@angular/forms';

const TooltipTranslations = {
  [ReportType.VAKATIEDOT_VOIMASSA]: VirkailijaTranslations.excel_report_type_description_vakatiedot_voimassa,
  [ReportType.PUUTTEELLISET_TOIMIPAIKKA]: VirkailijaTranslations.excel_report_type_description_puutteelliset_toimipaikka,
  [ReportType.PUUTTEELLISET_LAPSI]: VirkailijaTranslations.excel_report_type_description_puutteelliset_lapsi,
  [ReportType.PUUTTEELLISET_TYONTEKIJA]: VirkailijaTranslations.excel_report_type_description_puutteelliset_tyontekija,
  [ReportType.TYONTEKIJATIEDOT_VOIMASSA]: VirkailijaTranslations.excel_report_type_description_tyontekijatiedot_voimassa,
  [ReportType.TOIMIPAIKAT_VOIMASSA]: VirkailijaTranslations.excel_report_type_description_toimipaikat_voimassa,
  [ReportType.VUOSIRAPORTTI]: VirkailijaTranslations.excel_report_type_description_vuosiraportti,
  [ReportType.MAKSUTIETO_PUUTTUU_LAPSI]: VirkailijaTranslations.excel_report_type_description_maksutieto_puuttuu_lapsi,
};

@Component({
    selector: 'app-varda-excel-new',
    templateUrl: './varda-excel-new.component.html',
    styleUrls: ['./varda-excel-new.component.css'],
    standalone: false
})
export class VardaExcelNewComponent implements OnInit {
  @ViewChild('toimipaikkaSelector') toimipaikkaSelector: VardaAutocompleteSelectorComponent<VardaToimipaikkaMinimalDto>;
  errors: Observable<Array<ErrorTree>>;

  i18n = VirkailijaTranslations;

  toimipaikkaList: Array<VardaToimipaikkaMinimalDto> = [];
  henkilostoToimipaikkaList: Array<VardaToimipaikkaMinimalDto> = [];
  toimipaikkaOptions: Array<VardaToimipaikkaMinimalDto> = [];

  reportSubtypes = {
    [ReportType.VUOSIRAPORTTI]: [ReportSubtype.ALL, ReportSubtype.VARHAISKASVATUS, ReportSubtype.HENKILOSTO]
  };
  reportYears = {
    [ReportType.VUOSIRAPORTTI]: []
  };
  reportDatepickerOptions = {
    [ReportType.VUOSIRAPORTTI]: {
      datepickerMin: null,
      datepickerMax: null,
      datepickerSecondaryMin: null,
      datepickerSecondaryMax: new Date()
    }
  };

  datepickerMin: null;
  datepickerMax: null;
  datepickerSecondaryMin: null;
  datepickerSecondaryMax: null;

  reportTypeOptions: Array<Array<string>>;
  reportSubtypeOptions: Array<Array<string>>;
  yearOptions: Array<number>;

  newReport: VardaExcelReportPostDTO = {
    report_type: ReportType.VUOSIRAPORTTI,
    report_subtype: null,
    language: 'FI',
    organisaatio_oid: null,
    toimipaikka_oid: null,
    target_date: null,
    target_date_secondary: null
  };

  toimipaikkaSelectorReports = [
    ReportType.VAKATIEDOT_VOIMASSA.toString(),
    ReportType.TYONTEKIJATIEDOT_VOIMASSA.toString(),
    ReportType.TOIMIPAIKAT_VOIMASSA.toString(),
  ];
  dateSelectorReports = [
    ReportType.VAKATIEDOT_VOIMASSA.toString(),
    ReportType.TYONTEKIJATIEDOT_VOIMASSA.toString(),
    ReportType.TOIMIPAIKAT_VOIMASSA.toString(),
    ReportType.MAKSUTIETO_PUUTTUU_LAPSI.toString(),
  ];
  dateRangeSelectorReports = [];
  organisaatioSelectorReports = [
    ReportType.VUOSIRAPORTTI.toString(),
    ReportType.MAKSUTIETO_PUUTTUU_LAPSI.toString(),
  ];
  subtypeReports = [
    ReportType.VUOSIRAPORTTI.toString(),
  ];
  yearSelectorReports = [
    ReportType.VUOSIRAPORTTI.toString(),
  ];
  dateSecondarySelectorReports = [
    ReportType.VUOSIRAPORTTI.toString(),
  ];

  formGroup: FormGroup;

  isLoading = false;
  isOPHUser = false;

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
  ) {
    this.initReportYears();
  }

  ngOnInit() {
    this.isOPHUser = this.authService.isOPHUser || this.authService.isAdminUser;
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.errors = this.errorService.initErrorList();

    this.toimipaikkaList = this.vakajarjestajaService.getFilteredToimipaikat().katselijaToimipaikat;
    this.henkilostoToimipaikkaList = this.authService.getAuthorizedToimipaikat(this.toimipaikkaList,
      ViewAccess.henkilostotiedot);

    this.reportTypeOptions = Object.entries(ReportTypeTranslations).map(value => [value[0], value[1]]);

    this.newReport.language = this.translateService.currentLang;

    this.formGroup = new FormGroup({
      targetDate: new FormControl(DateTime.now()),
      targetDateSecondary: new FormControl(DateTime.now()),
      year: new FormControl(null),
      isOrganisaatioLevel: new FormControl(true),
      toimipaikka: new FormControl(null),
      isAllOrganisaatio: new FormControl(false)
    });

    this.reportTypeChange();
  }

  create() {
    const targetDateControl = this.formGroup.controls.targetDate;
    const targetDateSecondaryControl = this.formGroup.controls.targetDateSecondary;

    this.newReport.organisaatio_oid = this.vakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid;

    if (!this.formGroup.value.isOrganisaatioLevel && this.toimipaikkaSelectorReports.includes(this.newReport.report_type)) {
      const selectedToimipaikka = this.formGroup.value.toimipaikka;
      if (selectedToimipaikka && !this.toimipaikkaSelector.isOptionInvalid()) {
        this.newReport.toimipaikka_oid = selectedToimipaikka.organisaatio_oid;
      } else {
        this.newReport.toimipaikka_oid = null;
        this.toimipaikkaSelector.setInvalid();
        return;
      }
    }

    if (this.dateSelectorReports.includes(this.newReport.report_type)) {
      if (!targetDateControl.valid) {
        targetDateControl.markAsTouched();
        return;
      } else {
        this.newReport.target_date = this.dateService.luxonToVardaDate(targetDateControl.value);
      }
    }

    if (this.dateRangeSelectorReports.includes(this.newReport.report_type)) {
      if (!targetDateControl.valid || !targetDateSecondaryControl.valid) {
        targetDateControl.markAsTouched();
        targetDateSecondaryControl.markAsTouched();
        return;
      } else {
        this.newReport.target_date = this.dateService.luxonToVardaDate(targetDateControl.value);
        this.newReport.target_date_secondary = this.dateService.luxonToVardaDate(targetDateSecondaryControl.value);
      }
    }

    if (this.yearSelectorReports.includes(this.newReport.report_type)) {
      this.newReport.target_date = `${this.formGroup.controls.year.value}-12-31`;
    }

    if (this.dateSecondarySelectorReports.includes(this.newReport.report_type)) {
      if (!targetDateSecondaryControl.valid) {
        targetDateSecondaryControl.markAsTouched();
        return;
      } else {
        this.newReport.target_date_secondary = this.dateService.luxonToVardaDate(targetDateSecondaryControl.value);
      }
    }

    if (this.organisaatioSelectorReports.includes(this.newReport.report_type) &&
      this.formGroup.value.isAllOrganisaatio) {
      this.newReport.organisaatio_oid = null;
    }

    this.isLoading = true;
    this.raportitService.postExcelReport(this.newReport).subscribe({
      next: () => {
        this.router.navigate(['../'], {relativeTo: this.activatedRoute});
      }, error: error => {
        this.errorService.handleError(error, this.snackBarService);
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      }
    });
  }

  reportTypeChange() {
    this.formGroup.patchValue({
      isAllOrganisaatio: false,
      isOrganisaatioLevel: true,
      toimipaikka: null
    });

    this.newReport.toimipaikka_oid = null;
    this.newReport.report_subtype = null;
    this.newReport.target_date = null;
    this.newReport.target_date_secondary = null;

    this.setToimipaikkaOptions();
    this.setReportSubtypeOptions();
    this.setYearOptions();
    this.setDatePickerOptions();

    // Revalidate datepicker controls as different report types can have different validations
    setTimeout(() => {
      const targetDateControl = this.formGroup.controls.targetDate;
      const targetDateSecondaryControl = this.formGroup.controls.targetDateSecondary;
      targetDateControl.updateValueAndValidity();
      targetDateSecondaryControl.updateValueAndValidity();
      if (targetDateControl.invalid) {
        targetDateControl.markAsTouched();
      }
      if (targetDateSecondaryControl.invalid) {
        targetDateSecondaryControl.markAsTouched();
      }
    });
  }

  getTooltipTranslation(reportType: string) {
    return TooltipTranslations[reportType];
  }

  private initReportYears() {
    const currentYear = DateTime.now().year;
    const startYear = currentYear - 5;
    for (let i = startYear; i <= currentYear; i++) {
      if (i > 2019) {
        // Cannot create VUOSIRAPORTTI before 2019
        this.reportYears[ReportType.VUOSIRAPORTTI].push(i);
      }
    }
  }

  private setYearOptions() {
    this.yearOptions = [];
    if (this.reportYears[this.newReport.report_type]) {
      this.yearOptions = this.reportYears[this.newReport.report_type];
      this.formGroup.controls.year.setValue(this.yearOptions[this.yearOptions.length - 1]);
    }
  }

  private setToimipaikkaOptions() {
    switch (this.newReport.report_type) {
      case ReportType.VAKATIEDOT_VOIMASSA:
      case ReportType.TOIMIPAIKAT_VOIMASSA:
        this.toimipaikkaOptions = this.toimipaikkaList;
        break;
      case ReportType.TYONTEKIJATIEDOT_VOIMASSA:
        this.toimipaikkaOptions = this.henkilostoToimipaikkaList;
        break;
      default:
        break;
    }
  }

  private setReportSubtypeOptions() {
    this.reportSubtypeOptions = [];
    if (this.reportSubtypes[this.newReport.report_type]) {
      this.reportSubtypeOptions = this.reportSubtypes[this.newReport.report_type]
        .map(value => [value, ReportSubtypeTranslations[value]]);
      this.newReport.report_subtype = this.reportSubtypeOptions[0][0];
    }
  }

  private setDatePickerOptions() {
    this.datepickerMin = null;
    this.datepickerMax = null;
    this.datepickerSecondaryMin = null;
    this.datepickerSecondaryMax = null;

    if (this.reportDatepickerOptions[this.newReport.report_type]) {
      this.datepickerMin = this.reportDatepickerOptions[this.newReport.report_type].datepickerMin;
      this.datepickerMax = this.reportDatepickerOptions[this.newReport.report_type].datepickerMax;
      this.datepickerSecondaryMin = this.reportDatepickerOptions[this.newReport.report_type].datepickerSecondaryMin;
      this.datepickerSecondaryMax = this.reportDatepickerOptions[this.newReport.report_type].datepickerSecondaryMax;
    }
  }
}
