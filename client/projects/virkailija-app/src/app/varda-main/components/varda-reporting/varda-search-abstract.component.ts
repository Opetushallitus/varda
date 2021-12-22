import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CodeDTO, KoodistoDTO, KoodistoEnum, VardaKoodistoService } from 'varda-shared';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';
import { BreakpointObserver } from '@angular/cdk/layout';
import { TranslateService } from '@ngx-translate/core';
import { MatChipList } from '@angular/material/chips';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../core/auth/auth.service';
import { PaginatorParams, VardaResultListComponent } from './varda-result-list/varda-result-list.component';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { VardaKoosteApiService } from '../../../core/services/varda-kooste-api.service';

export enum FilterStringType {
  TRANSLATED_STRING = 'translatedString',
  RAW = 'raw'
}

export interface FilterStringParam {
  type: FilterStringType;
  value: string;
  ignoreComma?: boolean;
  lowercase?: boolean;
  ignoreSpace?: boolean;
}

export interface SearchResult {
  id: number;
  textPrimary: string;
  textSecondary?: string;
}

@Component({
  template: ''
})
export abstract class VardaSearchAbstractComponent implements OnInit, OnDestroy {
  @ViewChild('toimipaikkaInput') toimipaikkaInput: ElementRef<HTMLInputElement>;
  @ViewChild('toimipaikkaChipList') toimipaikkaChipList: MatChipList;
  @ViewChild('resultList') resultListComponent: VardaResultListComponent;

  i18n = VirkailijaTranslations;
  koodistoEnum = KoodistoEnum;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  vakajarjestajaName: string;

  resizeSubscription: Subscription;
  isSmall: boolean;

  translatedStringMap = {
    voimassa: this.i18n.katsele_tietoja_voimassa,
    paattynyt: this.i18n.katsele_tietoja_paattynyt,
    vakasuhteet: this.i18n.varhaiskasvatussuhde_plural,
    vakapaatokset: this.i18n.varhaiskasvatuspaatokset,
    maksutiedot: this.i18n.maksutiedot,
    alkanut: this.i18n.katsele_tietoja_alkanut,
    palvelussuhteet: this.i18n.palvelussuhteet,
    poissaolot: this.i18n.katsele_tietoja_tyontekija_poissaolot,
    taydennyskoulutukset: this.i18n.taydennyskoulutukset,
    aikavali: this.i18n.katsele_tietoja_aikavalilla,
    palveluseteli: this.i18n.katsele_tietoja_lapsi_palveluseteli,
    yes: this.i18n.yes,
    no: this.i18n.no
  };

  searchValue: string;
  isFiltersInactive = false;
  isFiltersVisible: boolean;

  toimipaikat: Array<VardaToimipaikkaMinimalDto> = [];
  selectedToimipaikat: Array<VardaToimipaikkaMinimalDto> = [];
  filteredToimipaikkaOptions: BehaviorSubject<Array<VardaToimipaikkaMinimalDto>> = new BehaviorSubject([]);
  isNoToimipaikkaResults = false;
  isAllToimipaikatSelected = true;

  filterString: string;
  resultCount = 0;
  searchResults: Array<SearchResult>;
  selectedId: number;

  pageSize = 20;

  userAccess: UserAccess;
  katselijaToimipaikat: Array<VardaToimipaikkaMinimalDto> = [];

  protected constructor(
    private koodistoService: VardaKoodistoService,
    private breakpointObserver: BreakpointObserver,
    private translateService: TranslateService,
    protected koosteService: VardaKoosteApiService,
    protected authService: AuthService,
    protected vakajarjestajaService: VardaVakajarjestajaService
  ) {
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
  }

  ngOnInit(): void {
    // Hide filters if screen size is small
    this.resizeSubscription = this.breakpointObserver.observe('(min-width: 768px)').subscribe(data => {
      this.isFiltersVisible = this.isFiltersFilled() || data.matches;
      this.isSmall = !data.matches;
    });

    this.vakajarjestajaName = this.vakajarjestajaService.getSelectedVakajarjestaja().nimi.trim().toLowerCase();
    this.katselijaToimipaikat = this.vakajarjestajaService.getFilteredToimipaikat().katselijaToimipaikat;
    this.authService.getToimipaikkaAccessToAnyToimipaikka().subscribe(accessIfAny => {
      this.userAccess = accessIfAny;
      this.afterUserAccessInit();
    });
  }

  getKoodistoFromKoodistoService(name: KoodistoEnum): Observable<KoodistoDTO> {
    return this.koodistoService.getKoodisto(name);
  }

  getCodeUiString(code: CodeDTO | null): string {
    if (!code) {
      return null;
    }
    return `${code.name} (${code.code_value})`;
  }

  getFilterString(params: Array<FilterStringParam>): string {
    let resultString = '';

    params.forEach((param, index) => {
      if (!param.value) {
        return;
      }

      if (resultString !== '') {
        resultString += param.ignoreComma ? '' : ',';
        resultString += param.ignoreSpace ? '' : ' ';
      }

      let newValue;
      switch (param.type) {
        case FilterStringType.TRANSLATED_STRING:
          newValue = this.translateService.instant(this.translatedStringMap[param.value]);
          break;
        case FilterStringType.RAW:
        default:
          newValue = param.value;
      }

      resultString += param.lowercase ? newValue.toLowerCase() : newValue;
    });

    return resultString;
  }

  toimipaikkaAutocompleteSelected(event: MatAutocompleteSelectedEvent) {
    const selectedToimipaikka = event.option.value;

    if (selectedToimipaikka) {
      this.isAllToimipaikatSelected = false;
      this.selectedToimipaikat.push(selectedToimipaikka);

      // Remove selected option from Autocomplete
      this.filteredToimipaikkaOptions.next(this.toimipaikat.filter(toimipaikka => toimipaikka.id !== selectedToimipaikka.id && this.selectedToimipaikat.indexOf(toimipaikka) === -1));
    } else {
      // All toimipaikat selection is applied
      this.isAllToimipaikatSelected = true;
      this.selectedToimipaikat = [];
      this.filteredToimipaikkaOptions.next([...this.toimipaikat]);
    }

    this.toimipaikkaInput.nativeElement.value = '';
    setTimeout(() => {
      this.toimipaikkaChipList.chips.last.focus();
    });
    this.isNoToimipaikkaResults = false;

    this.search();
  }

  removeSelectedToimipaikka(removedToimipaikka: VardaToimipaikkaMinimalDto) {
    if (removedToimipaikka) {
      this.selectedToimipaikat.splice(this.selectedToimipaikat.indexOf(removedToimipaikka), 1);

      // Add removed option back to Autocomplete
      this.filteredToimipaikkaOptions.next(this.toimipaikat.filter(toimipaikka => this.selectedToimipaikat.indexOf(toimipaikka) === -1));
    } else {
      // Reset input if all toimipaikat selection is cleared
      this.isAllToimipaikatSelected = false;
      this.filteredToimipaikkaOptions.next([...this.toimipaikat]);
    }

    this.toimipaikkaInput.nativeElement.value = '';
    this.isNoToimipaikkaResults = false;

    this.search();
  }

  toimipaikkaSelectInputChange(event: Event) {
    const targetValue = (event.target as HTMLInputElement).value;
    const results = this.toimipaikat.filter(toimipaikka => toimipaikka.nimi.toLowerCase().includes(targetValue.toLowerCase()) && this.selectedToimipaikat.indexOf(toimipaikka) === -1);

    if (results.length === 0) {
      this.isNoToimipaikkaResults = true;
      this.filteredToimipaikkaOptions.next([]);
    } else {
      this.isNoToimipaikkaResults = false;
      this.filteredToimipaikkaOptions.next(results);
    }
  }

  getSecondaryText(vakajarjestaja: string): string | null {
    if (!vakajarjestaja) {
      return null;
    }

    return vakajarjestaja.trim().toLowerCase() !== this.vakajarjestajaName ? vakajarjestaja : null;
  }

  setPaginatorParams(searchParams: Record<string, unknown>, paginatorParams?: PaginatorParams): Record<string, unknown> {
    if (paginatorParams) {
      this.pageSize = paginatorParams.pageSize;
    }

    searchParams.page = paginatorParams ? paginatorParams.page : 1;
    searchParams.page_size = paginatorParams ? paginatorParams.pageSize : this.pageSize;
    return searchParams;
  }

  setSelectedId(id: number) {
    setTimeout(() => {
      this.selectedId = id;
    });
  }

  afterUserAccessInit(): void {
    return;
  }

  ngOnDestroy(): void {
    this.resizeSubscription.unsubscribe();
  }

  abstract isFiltersFilled(): boolean;
  abstract search(paginatorParams?: PaginatorParams): void;
}
