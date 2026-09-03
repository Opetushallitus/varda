import {Input, Output, EventEmitter, OnDestroy, Component, OnInit, ViewChild, ElementRef} from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { TranslateService } from '@ngx-translate/core';
import { VardaErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaUtilityService } from 'projects/virkailija-app/src/app/core/services/varda-utility.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { Subscription, BehaviorSubject, Observable } from 'rxjs';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from '../../../../utilities/models/varda-vakajarjestaja-ui.model';
import {map, startWith} from 'rxjs/operators';
import {VardaPageDto} from '../../../../utilities/models/dto/varda-page-dto';
import {FormControl} from "@angular/forms";
import {MatChipInputEvent} from "@angular/material/chips";
import {MatAutocompleteSelectedEvent} from "@angular/material/autocomplete";
import {COMMA, ENTER} from "@angular/cdk/keycodes";
import {KoodistoEnum} from "varda-shared";
import {
  PuutteellinenOrganisaatioListDTO,
  PuutteellinenToimipaikkaListDTO
} from "../../../../utilities/models/dto/varda-puutteellinen-dto.model";
import {HenkiloListDTO} from "../../../../utilities/models/dto/varda-henkilo-dto.model";

export interface PuutteellinenSearchFilter {
  page: number;
  page_size: number;
  search?: string;
  count?: number;
  error?: string;
  rows_filter?: string;
  exclude_errors?: boolean;
}

export class PuutteellinenPageDto<T> extends VardaPageDto<T> {
  error_codes: Array<string>;
}

@Component({
    template: '',
    standalone: false
})
export abstract class AbstractPuutteellisetComponent<T, Y> implements OnInit, OnDestroy {
  @Input() selectedToimipaikka: VardaToimipaikkaMinimalDto;
  @Output() openHenkiloForm = new EventEmitter<Y>(true);
  @Output() openToimipaikkaForm = new EventEmitter<Y>(true);
  @ViewChild('errorCodeInput') errorCodeInput: ElementRef<HTMLInputElement>;

  koodistoEnum = KoodistoEnum;

  separatorKeysCodes: number[] = [ENTER, COMMA];
  errorCodeCtrl = new FormControl('');
  filteredErrorCodes: Observable<string[]>;
  selectedErrorCodes: string[] = [];

  filteredRowsKey: string;
  filteredRowIds: number[] = [];
  filteredRows: Array<PuutteellinenToimipaikkaListDTO|HenkiloListDTO|PuutteellinenOrganisaatioListDTO> = [];
  lastRemovedIndices: number[] = [];

  errorCodes: Array<string>;
  errorCodesKey: string;
  excludeErrorCodes = false;

  selectedVakajarjestaja: VardaVakajarjestajaUi;
  formErrors: Observable<Array<ErrorTree>>;
  subscriptions: Array<Subscription> = [];
  isLoading = new BehaviorSubject<boolean>(false);
  searchFilter: PuutteellinenSearchFilter = {
    page_size: 20,
    page: 1,
    count: 0,
  };
  protected errorService: VardaErrorMessageService;

  constructor(
    protected utilityService: VardaUtilityService,
    protected translateService: TranslateService,
    vakajarjestajaService: VardaVakajarjestajaService,
  ) {
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.formErrors = this.errorService.initErrorList();
    this.selectedVakajarjestaja = vakajarjestajaService.getSelectedVakajarjestaja();
  }

  ngOnInit() {
    const savedErrorCodes = localStorage.getItem(this.errorCodesKey);
    if (savedErrorCodes) {
      this.selectedErrorCodes = JSON.parse(savedErrorCodes);
    }
    this.searchFilter.error = this.selectedErrorCodes.join(',');

    this.getErrors();
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }

  getFilter(): PuutteellinenSearchFilter {
    const cleanSearchFilter: PuutteellinenSearchFilter = {
      page: null,
      page_size: null,
    };

    Object.entries(this.searchFilter).filter(
      ([, value]) => value).forEach(([key, value]) => cleanSearchFilter[key] = this.utilityService.hashHetu(value)
    );

    return cleanSearchFilter;
  }

  searchErrors(pageEvent?: PageEvent) {
    if (pageEvent) {
      this.searchFilter.page = pageEvent.pageIndex + 1;
      this.searchFilter.page_size = pageEvent.pageSize;
    } else {
      this.searchFilter.page = 1;
    }

    if (this.excludeErrorCodes) {
      this.searchFilter.exclude_errors = this.excludeErrorCodes;
    } else {
      delete this.searchFilter.exclude_errors;
    }

    this.searchFilter.error = this.selectedErrorCodes.join(',');
    this.searchFilter.rows_filter = this.filteredRowIds.join(',');
    localStorage.setItem(this.errorCodesKey, JSON.stringify(this.selectedErrorCodes));
    localStorage.setItem(this.filteredRowsKey, JSON.stringify(this.filteredRows));
    this.getErrors();
  }

  setFilteredErrorCodes() {
    this.filteredErrorCodes = this.errorCodeCtrl.valueChanges.pipe(
      startWith(null),
      map((errorCode: string | null) => (errorCode ? this.filter(errorCode) : this.errorCodes.slice())),
    );
  }

  removeErrorCodeFromList(errorCode: string): void {
    const index = this.errorCodes.indexOf(errorCode);
    if (index !== -1) {
      this.errorCodes.splice(index, 1);
      this.setFilteredErrorCodes(); // Update the filtered error codes
    }
  }

  addErrorCodeToList(errorCode: string): void {
    this.errorCodes.push(errorCode);
    this.setFilteredErrorCodes(); // Update the filtered error codes
  }

  add(event: MatChipInputEvent): void {

    const selectedValue = (event.value || '').trim();
    if (selectedValue) {
      this.selectedErrorCodes.push(selectedValue);
    }

    // Clear the input value
    event.chipInput!.clear();

    this.errorCodeCtrl.setValue(null);
  }

  remove(errorCode: string): void {
    const index = this.selectedErrorCodes.indexOf(errorCode);

    if (index !== -1) {
      this.selectedErrorCodes.splice(index, 1);
      this.addErrorCodeToList(errorCode); // Add back to available error codes
    }
  }

selected(event: MatAutocompleteSelectedEvent): void {
  const selectedErrorCode = event.option.viewValue.slice(0, 5);
  this.selectedErrorCodes.push(selectedErrorCode);
  this.removeErrorCodeFromList(selectedErrorCode); // Remove from available error codes
  this.errorCodeInput.nativeElement.value = '';
  this.errorCodeCtrl.setValue(null);
}

   filter(value: string): string[] {
    const filterValue = value.toLowerCase();

    return this.errorCodes.filter(errorCode => errorCode.toLowerCase().includes(filterValue));
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  filterClicked(instance: T): void {
    this.searchFilter.count = this.searchFilter.count - 1;
    this.searchFilter.rows_filter = this.filteredRowIds.join(',');
    localStorage.setItem(this.filteredRowsKey, JSON.stringify(this.filteredRows));
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  removeFilteredRowChip(instance: T): void {
    this.searchFilter.count = this.searchFilter.count + 1;
    this.searchFilter.rows_filter = this.filteredRowIds.join(',');
    localStorage.setItem(this.filteredRowsKey, JSON.stringify(this.filteredRows));
  }

  abstract getErrors(): void;
  abstract errorClicked(instance: T): void;
  abstract openForm(instance: Y): void;
}
