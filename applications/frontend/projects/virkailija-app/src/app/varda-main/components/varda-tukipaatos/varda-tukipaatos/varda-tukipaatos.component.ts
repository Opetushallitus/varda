import {Component, OnInit} from '@angular/core';
import {UserAccess} from "../../../../utilities/models/varda-user-access.model";
import {VirkailijaTranslations} from "../../../../../assets/i18n/virkailija-translations.enum";
import {FormArray, FormControl, FormGroup, Validators} from "@angular/forms";
import {VardaVakajarjestajaService} from "../../../../core/services/varda-vakajarjestaja.service";
import {VardaVakajarjestajaApiService} from "../../../../core/services/varda-vakajarjestaja-api.service";
import {KoodistoEnum, LoadingHttpService} from "varda-shared";
import {AuthService} from "../../../../core/auth/auth.service";
import {VardaSnackBarService} from "../../../../core/services/varda-snackbar.service";
import {TranslateService} from "@ngx-translate/core";
import {ErrorTree, VardaErrorMessageService} from "../../../../core/services/varda-error-message.service";
import {concatMap, EMPTY, from, Observable, toArray} from "rxjs";
import {VardaVakajarjestajaUi} from "../../../../utilities/models/varda-vakajarjestaja-ui.model";
import {VardaLapsiService} from "../../../../core/services/varda-lapsi.service";
import {VardaTukipaatosDTO, VardaTukipaatosListsDTO} from "../../../../utilities/models/dto/varda-tukipaatos-dto.model";
import {catchError, switchMap} from "rxjs/operators";
import {Lahdejarjestelma} from "../../../../utilities/models/enums/hallinnointijarjestelma";
import {VardaPageDto} from "../../../../utilities/models/dto/varda-page-dto";

interface TableData {
  ikaryhma_koodi: string;
  formData?: FormData;
}

interface FormData {
  [key: string]: FormGroup | string;
}

export interface TukipaatosSearchFilter {
  vakajarjestaja?: string;
  yksityinen_jarjestaja?: boolean;
  tilastointi_pvm?: string;
  ikaryhma_koodi?: string;
  tuentaso_koodi?: string;
  page_size?: number;
}

type Summary = Record<string, number>;

@Component({
    selector: 'app-varda-tukipaatos',
    templateUrl: './varda-tukipaatos.component.html',
    styleUrls: ['./varda-tukipaatos.component.css'],
    standalone: false
})
export class VardaTukipaatosComponent implements OnInit {
  koodistoEnum = KoodistoEnum;
  tuenTasoKoodiList: string[] = []
  columnsToDisplay: string[];
  toimijaAccess: UserAccess;
  i18n = VirkailijaTranslations;
  isSubmitting: Observable<boolean>;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  ageGroupList: string[] = [];
  statisticalDateList: string[] = [];
  selectedStatisticalDate: string;
  isTimeframeEditable: boolean;
  tukipaatosFormErrors: Observable<Array<ErrorTree>>;
  lastUpdated: Date;

  // Municipal
  municipalDataSource: Array<TableData>;
  municipalFormArray: FormArray = new FormArray([]);
  initialMunicipalFormValues: any;
  isMunicipalEdit: boolean;
  municipalToggle = { value: false, disabled: true };

  // Private
  privateDataSource: Array<TableData>;
  privateFormArray: FormArray = new FormArray([]);
  initialPrivateFormValues: any;
  isPrivateEdit: boolean;
  privateToggle = { value: false, disabled: true };


  protected readonly isNaN = isNaN;
  private tukipaatosErrorService: VardaErrorMessageService;
  private editLock: 'municipal' | 'private' | null = null;

  constructor(
    private vakajarjestajaService: VardaVakajarjestajaService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private http: LoadingHttpService,
    private authService: AuthService,
    private VardaLapsiService: VardaLapsiService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService
  ) {
    this.isSubmitting = this.http.isLoading();
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    this.tukipaatosErrorService = new VardaErrorMessageService(translateService);
    this.tukipaatosFormErrors = this.tukipaatosErrorService.initErrorList();
  }

  ngOnInit() {
    this.toimijaAccess = this.authService.getUserAccess();
    this.initiateTukipaatokset();
  }

  disableMunicipalForm() {
    this.resetMunicipalFormToInitialValues();
    this.isMunicipalEdit = false;
    this.municipalFormArray.disable();
    this.editLock = null;
  }

  disablePrivateForm() {
    this.resetPrivateFormToInitialValues();
    this.isPrivateEdit = false;
    this.privateFormArray.disable();
    this.editLock = null;
  }

  resetMunicipalFormToInitialValues() {
    this.municipalFormArray.patchValue(this.initialMunicipalFormValues);
  }

  resetPrivateFormToInitialValues() {
    this.privateFormArray.patchValue(this.initialPrivateFormValues);
  }

  enableMunicipalForm() {
    if (this.editLock && this.editLock !== 'municipal') {
      return;
    }

    if (!this.municipalToggle.disabled) {
      this.editLock = 'municipal';
      this.isMunicipalEdit = true;
      this.municipalFormArray.enable();
    }
  }

  enablePrivateForm() {
    if (this.editLock && this.editLock !== 'private') {
      return;
    }

    if (!this.privateToggle.disabled) {
      this.editLock = 'private';
      this.isPrivateEdit = true;
      this.privateFormArray.enable();
    }
  }

  selectChange(selectedStatisticalDate: string) {
    this.selectedStatisticalDate = selectedStatisticalDate;
    this.initiateTukipaatokset();
  }

  saveTukipaatokset(isPrivate: boolean) {
    const formArray = isPrivate ? this.privateFormArray : this.municipalFormArray;

    if (isPrivate) {
      this.isPrivateEdit = false;
    } else {
      this.isMunicipalEdit = false;
    }

    const requestsToSend = formArray.controls
      .filter(formGroup => formGroup.valid && !formGroup.pristine)
      .map(formGroup => {
        /* Set all 'null' values to 0 */
        if (formGroup.value.paatosmaara === null) {
          formGroup.value.paatosmaara = 0;
          formGroup.markAsDirty();
        }

        formGroup.markAsPristine();
        return formGroup.value;
      });

    from(requestsToSend).pipe(
      concatMap(value =>
        this.VardaLapsiService.saveTukipaatokset(value).pipe(
          catchError(err => {
            this.tukipaatosErrorService.handleError(err);
            return EMPTY;
          })
        )
      ),
      toArray() // wait for all requests to finish
    ).subscribe({
      next: () => {
        this.editLock = null;
        this.isMunicipalEdit = false;
        this.isPrivateEdit = false;
        this.initiateTukipaatokset();
        this.snackBarService.success(this.i18n.tuen_tiedot_save_success);
      },
      error: (err) => this.tukipaatosErrorService.handleError(err, this.snackBarService)
    });
  }

  transformData(data: VardaTukipaatosDTO[], isPrivate: boolean): TableData[] {
    /* Function to transform the data to the format we need in the table */
    const result: TableData[] = [];

    this.ageGroupList.forEach((ikaryhma_koodi: string) => {
      const newData: TableData = { ikaryhma_koodi };
      this.tuenTasoKoodiList.forEach((tukipaatosKoodi: string) => {
        const matchingItem = data.find(
          item => {
           if (item.ikaryhma_koodi === ikaryhma_koodi && item.tuentaso_koodi === tukipaatosKoodi) {
             return true;
           }
          }
        );
        if (matchingItem) {
          newData[tukipaatosKoodi] = this.newFormGroup(matchingItem);
        }
        else {
          newData[tukipaatosKoodi] = this.newFormGroup(this.emptyTukipaatos(ikaryhma_koodi, tukipaatosKoodi, isPrivate));
        }
      });

      result.push(newData);
    });

    return result;
  }

  emptyTukipaatos(ikaryhma_koodi: string, tuentaso_koodi: string, isPrivate: boolean): VardaTukipaatosDTO {
    return {
      id: null,
      vakajarjestaja_oid: this.selectedVakajarjestaja.organisaatio_oid,
      paatosmaara: null,
      yksityinen_jarjestaja: isPrivate,
      ikaryhma_koodi: ikaryhma_koodi,
      tuentaso_koodi: tuentaso_koodi,
      lahdejarjestelma: Lahdejarjestelma.kayttoliittyma,
    };
  }


  newFormGroup(tukipaatosData: VardaTukipaatosDTO): FormGroup {
    return new FormGroup({
      id: new FormControl(tukipaatosData.id),
      vakajarjestaja_oid: new FormControl(tukipaatosData.vakajarjestaja_oid),
      paatosmaara: new FormControl(tukipaatosData.paatosmaara, [...this.paatosmaaraValidators()]),
      yksityinen_jarjestaja: new FormControl(tukipaatosData.yksityinen_jarjestaja),
      ikaryhma_koodi: new FormControl(tukipaatosData.ikaryhma_koodi),
      tuentaso_koodi: new FormControl(tukipaatosData.tuentaso_koodi),
      lahdejarjestelma: new FormControl(tukipaatosData.lahdejarjestelma),
    });
  }

  convertFormArray(resultData: TableData[]): FormArray {
    const tukipaatosFormArray: FormArray = new FormArray([]);
    resultData.forEach((data) => {
      for (const key in data) {
        if (key === 'ikaryhma_koodi') {
          continue;
        }
        tukipaatosFormArray.push(data[key]);
      }
    });
    return tukipaatosFormArray;
  }

  createSummaryRow(summary): TableData {
    const summaryRow: TableData = { ikaryhma_koodi: this.i18n.tuen_tiedot_yhteensa };

    for (const key in this.tuenTasoKoodiList) {
      if (summary.hasOwnProperty(this.tuenTasoKoodiList[key])) {
        summaryRow[this.tuenTasoKoodiList[key]] = summary[this.tuenTasoKoodiList[key]];
      } else {
        summaryRow[this.tuenTasoKoodiList[key]] = 0;
      }
    }

    return summaryRow;
  }

  calculatePaatosmaaraSumByTukipaatosKoodi(data: VardaTukipaatosDTO[]): Summary {
    const summary: Summary = {};

    data.forEach((item) => {
      const { tuentaso_koodi, paatosmaara } = item;

      if (summary[tuentaso_koodi] === undefined) {
        summary[tuentaso_koodi] = paatosmaara;
      } else {
        summary[tuentaso_koodi] += paatosmaara;
      }
    });
    return summary;
  }

  municipalTukipaatokset(data: VardaTukipaatosDTO[]) {
    this.municipalToggle.disabled = false;
    this.municipalDataSource = this.transformData(data, false);
    this.municipalFormArray = this.convertFormArray(this.municipalDataSource);
    this.initialMunicipalFormValues = this.municipalFormArray.value;
    const summaryRow: TableData = this.createSummaryRow(this.calculatePaatosmaaraSumByTukipaatosKoodi(data))
    this.municipalDataSource.push(summaryRow)
  }

  privateTukipaatokset(data: VardaTukipaatosDTO[]) {
    this.privateToggle.disabled = false;
    this.privateDataSource = this.transformData(data, true);
    this.privateFormArray = this.convertFormArray(this.privateDataSource);
    this.initialPrivateFormValues = this.privateFormArray.value;
    const summaryRow: TableData = this.createSummaryRow(this.calculatePaatosmaaraSumByTukipaatosKoodi(data))
    this.privateDataSource.push(summaryRow)
  }

  isDateWithinTimeframe(startDate: Date, endDate: Date, dateToCheck: Date): boolean {
    return dateToCheck >= startDate && dateToCheck <= endDate;
  }

  setInitialSelectValue(isTodayWithinTimeframe: boolean, nextStatisticalDate: string) {
    // Set the initial select value
    if (!this.selectedStatisticalDate) {
      // First check if today is within timeframe and set it as selected
      if (isTodayWithinTimeframe) {
        // Reverse the date format to match the format in the select
        this.selectedStatisticalDate = this.reverseDateFormat(nextStatisticalDate);
      } else { // If not, set the latest statistical date as selected
        this.selectedStatisticalDate = this.statisticalDateList[this.statisticalDateList.length - 1];
      }
    }
  }

  compareDatesByYMD(date1: Date, date2: Date) {
    return (
      date1.getFullYear() === date2.getFullYear() &&
      date1.getMonth() === date2.getMonth() &&
      date1.getDate() === date2.getDate()
    );
  }

  reverseDateFormat(date: string) {
    return date.split('-').reverse().join('-');
  }

  normalizeDate(date: Date): Date {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  initiateTimeframeConfigurations(data: VardaTukipaatosListsDTO) {
    const nextStartDate = new Date(data.next_aikavali.alkamis_pvm)
    const normalizedStartDate = this.normalizeDate(nextStartDate);
    const nextEndDate = new Date(data.next_aikavali.paattymis_pvm)
    const normalizedEndDate = this.normalizeDate(nextEndDate);
    const nextStatisticalDate = data.next_aikavali.tilastointi_pvm;
    const today = new Date();
    const normalizedToday = this.normalizeDate(today);

    const isTodayWithinTimeframe = this.isDateWithinTimeframe(normalizedStartDate, normalizedEndDate, normalizedToday);
    this.setInitialSelectValue(isTodayWithinTimeframe, nextStatisticalDate);
    const isSelectedStatisticalDateWithinTimeframe = this.isDateWithinTimeframe(
      normalizedStartDate, normalizedEndDate, new Date(this.reverseDateFormat(this.selectedStatisticalDate)));

    this.isTimeframeEditable = isTodayWithinTimeframe && isSelectedStatisticalDateWithinTimeframe;

    // Reverse the date format to match the format in the select
    if (!this.statisticalDateList.includes(this.reverseDateFormat(nextStatisticalDate)) && isTodayWithinTimeframe) {
      this.statisticalDateList.push(this.reverseDateFormat(nextStatisticalDate));
    }
  }

  getFilter(
    pageSize: number = null,
    vakajarjestaja: string,
    tilastointiPvm: string = null,
  ): TukipaatosSearchFilter {
    const filter: TukipaatosSearchFilter = {
      vakajarjestaja: vakajarjestaja,
    };

    if (tilastointiPvm !== null) {
      filter.tilastointi_pvm = tilastointiPvm;
    }

    filter.page_size = pageSize;

    return filter;
  }

  setLastUpdated(data: VardaPageDto<VardaTukipaatosDTO>) {
  // Use the reduce to find the latest muutos_pvm
    this.lastUpdated = data.results.reduce((latestDate: Date | null, item: VardaTukipaatosDTO) => {
    // Extract muutos_pvm from the current item and convert it to a Date object
    const muutosPvm = item.muutos_pvm ? new Date(item.muutos_pvm) : null;

    // If muutosPvm exists and is later than the current latestDate, update latestDate
    if (muutosPvm && (!latestDate || muutosPvm > latestDate)) {
      latestDate = muutosPvm;
    }

    return latestDate;
  }, null);
  }

  initiateTukipaatokset() {
    this.VardaLapsiService.getTukipaatosLists()
      .pipe(
        switchMap(data => {
          this.ageGroupList = data.ikaryhma_koodi_list;
          this.tuenTasoKoodiList = data.tuentaso_koodi_list;
          this.statisticalDateList = data.tilastointi_pvm_list.map((dateString) => {
            return this.reverseDateFormat(dateString) // Display dates in correct order in select
          });

          this.initiateTimeframeConfigurations(data);

          // Reverse so select dates will display in correct order
          this.statisticalDateList.reverse();

          // initiate table columns
          this.columnsToDisplay = ['ikaryhma_koodi', ...this.tuenTasoKoodiList];
          const pageSize = this.ageGroupList.length * this.tuenTasoKoodiList.length * 2
          return this.VardaLapsiService.getTukipaatokset(this.getFilter(
            pageSize,
            this.selectedVakajarjestaja.organisaatio_oid,
            this.reverseDateFormat(this.selectedStatisticalDate))); // Reverse date format for API call
        })
      )
      .subscribe({
        next: data => {
          this.setLastUpdated(data);
          const municipalData = data.results.filter(item => !item.yksityinen_jarjestaja);
          this.municipalTukipaatokset(municipalData);
          const privateData = data.results.filter(item => item.yksityinen_jarjestaja);
          this.privateTukipaatokset(privateData);
        },
        error: err => this.tukipaatosErrorService.handleError(err, this.snackBarService),
      });
  }

  valueChanged(paatosmaara: FormControl) {
    if (paatosmaara.value === null) {
      paatosmaara.setValidators([...this.paatosmaaraValidators(), Validators.required]);
    } else {
      paatosmaara.setValidators([...this.paatosmaaraValidators()]);
    }

    paatosmaara.updateValueAndValidity();
  }

  private paatosmaaraValidators() {
    return [
      Validators.pattern(/^-?\d+$/), // Validates for integers (positive or negative)
      Validators.max(9999)
    ];
  }

}
