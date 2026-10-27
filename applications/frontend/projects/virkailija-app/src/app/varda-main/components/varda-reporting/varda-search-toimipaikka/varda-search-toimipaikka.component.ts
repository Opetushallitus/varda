import { Component, OnInit } from '@angular/core';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import {
  FilterStringParam,
  FilterStringType,
  VardaSearchAbstractComponent
} from '../varda-search-abstract.component';
import { CodeDTO, VardaDateService, VardaKoodistoService } from 'varda-shared';
import { BreakpointObserver } from '@angular/cdk/layout';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../../../core/auth/auth.service';
import { PaginatorParams } from '../varda-result-list/varda-result-list.component';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';
import { DateTime } from 'luxon';
import { extractCursor } from "../../../../utilities/helper-functions";

@Component({
    selector: 'app-varda-search-toimipaikka',
    templateUrl: './varda-search-toimipaikka.component.html',
    styleUrls: ['./varda-search-toimipaikka.component.css'],
    standalone: false
})
export class VardaSearchToimipaikkaComponent extends VardaSearchAbstractComponent implements OnInit {
  voimassaolo = {
    KAIKKI: 'kaikki',
    ALKANUT: 'alkanut',
    PAATTYNYT: 'paattynyt',
    VOIMASSA: 'voimassa'
  };

  filterParams: {
    toimintamuoto: CodeDTO;
    jarjestamismuoto: CodeDTO;
    voimassaolo: string;
    alkamisPvm: DateTime;
    paattymisPvm: DateTime;
  } = {
    toimintamuoto: null,
    jarjestamismuoto: null,
    voimassaolo: this.voimassaolo.VOIMASSA,
    alkamisPvm: DateTime.now(),
    paattymisPvm: DateTime.now()
  };
  voimassaoloPrevious = this.filterParams.voimassaolo;

  constructor(
    koodistoService: VardaKoodistoService,
    breakpointObserver: BreakpointObserver,
    translateService: TranslateService,
    koosteService: VardaKoosteApiService,
    vakajarjestajaService: VardaVakajarjestajaService,
    authService: AuthService,
    private dateService: VardaDateService,
  ) {
    super(koodistoService, breakpointObserver, translateService, koosteService, authService, vakajarjestajaService);
  }

  ngOnInit() {
    super.ngOnInit();
    this.search();
  }

  search(paginatorParams?: PaginatorParams): any {
    const continueSearch = this.filter();
    if (!continueSearch) {
      return;
    }

    if (this.searchInput && !this.searchInput.valid) {
      return;
    }

    const searchParams: Record<string, unknown> = {};
    this.setPaginatorParams(searchParams, paginatorParams);

    this.updateFilterString();

    if (this.searchValue) {
      searchParams.search = this.searchValue;
    }
    if (this.filterParams.jarjestamismuoto) {
      searchParams.jarjestamismuoto_koodi = this.filterParams.jarjestamismuoto.code_value.toLowerCase();
    }
    if (this.filterParams.toimintamuoto) {
      searchParams.toimintamuoto_koodi = this.filterParams.toimintamuoto.code_value.toLowerCase();
    }

    const alkamisPvm = this.dateService.luxonToVardaDate(this.filterParams.alkamisPvm);
    const paattymisPvm = this.dateService.luxonToVardaDate(this.filterParams.paattymisPvm);
    switch (this.filterParams.voimassaolo) {
      case this.voimassaolo.VOIMASSA:
        searchParams.alkamis_pvm_before = alkamisPvm;
        searchParams.paattymis_pvm_after = paattymisPvm;
        break;
      case this.voimassaolo.PAATTYNYT:
        searchParams.paattymis_pvm_after = alkamisPvm;
        searchParams.paattymis_pvm_before = paattymisPvm;
        break;
      case this.voimassaolo.ALKANUT:
        searchParams.alkamis_pvm_after = alkamisPvm;
        searchParams.alkamis_pvm_before = paattymisPvm;
    }

    if (!paginatorParams && this.resultListComponent) {
      this.resultListComponent.resetResults();
    }

    this.koosteService.getToimipaikatForVakajarjestaja(this.selectedVakajarjestaja.id, searchParams)
      .subscribe(response => {
        this.resultCount = response.count;
        this.nextCursor = extractCursor(response.next);
        this.prevCursor = extractCursor(response.previous);
        this.searchResults = response.results.map(toimipaikka => ({
            id: toimipaikka.id,
            textPrimary: toimipaikka.nimi_original,
            textSecondary: this.getSecondaryText(toimipaikka.paos_organisaatio_nimi)
          }));
      });
  }

  filter(): boolean {
    if (this.voimassaoloPrevious === this.voimassaolo.KAIKKI &&
      this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI) {
      // initialize voimassaolo filters
      this.fillFilters1();
    }
    this.voimassaoloPrevious = this.filterParams.voimassaolo;

    if (this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI && !this.isFilters1Filled()) {
      // voimassaolo filter is in use but not all filters are valid, do not continue search
      return false;
    }

    return true;
  }

  isFiltersActive(): boolean {
    return this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI || this.isFilters2Filled();
  }

  fillFilters1() {
    this.filterParams.alkamisPvm = DateTime.now();
    this.filterParams.paattymisPvm = DateTime.now();
  }

  fillFilters2() {}
  fillFilters3() {}

  isFilters1Filled(): boolean {
    return this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI && this.filterParams.alkamisPvm !== null &&
      this.filterParams.paattymisPvm !== null;
  }

  isFilters2Filled(): boolean {
    return this.filterParams.jarjestamismuoto !== null || this.filterParams.toimintamuoto !== null;
  }

  isFilters3Filled(): boolean {
    return false;
  }

  clearFilters1() {
    this.filterParams.voimassaolo = this.voimassaolo.KAIKKI;
    this.filterParams.alkamisPvm = null;
    this.filterParams.paattymisPvm = null;
  }

  clearFilters2() {
    this.filterParams.toimintamuoto = null;
    this.filterParams.jarjestamismuoto = null;
  }

  clearFilters3() {}

  updateFilterString() {
    const stringParams: Array<FilterStringParam> = [];

    if (this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI) {
      stringParams.push({ value: this.filterParams.voimassaolo, type: FilterStringType.TRANSLATED_STRING });
      this.addDateRangeFilterString(stringParams);
    }

    stringParams.push({ value: this.getCodeUiString(this.filterParams.toimintamuoto), type: FilterStringType.RAW, lowercase: true });
    stringParams.push({ value: this.getCodeUiString(this.filterParams.jarjestamismuoto), type: FilterStringType.RAW, lowercase: true });

    setTimeout(() => {
      this.filterString = this.getFilterString(stringParams);
    });
  }
}
