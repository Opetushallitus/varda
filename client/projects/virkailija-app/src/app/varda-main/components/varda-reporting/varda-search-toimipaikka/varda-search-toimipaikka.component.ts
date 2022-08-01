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
import * as moment from 'moment';
import { AuthService } from '../../../../core/auth/auth.service';
import { PaginatorParams } from '../varda-result-list/varda-result-list.component';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';
import { Moment } from 'moment';

@Component({
  selector: 'app-varda-search-toimipaikka',
  templateUrl: './varda-search-toimipaikka.component.html',
  styleUrls: ['./varda-search-toimipaikka.component.css']
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
    alkamisPvm: Moment;
    paattymisPvm: Moment;
  } = {
      toimintamuoto: null,
      jarjestamismuoto: null,
      voimassaolo: this.voimassaolo.VOIMASSA,
      alkamisPvm: moment(),
      paattymisPvm: moment()
    };

  isTimeFilterInactive = false;

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
    this.isFilters1Active = false;
    this.isFilters2Active = false;
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

    const alkamisPvm = this.dateService.momentToVardaDate(this.filterParams.alkamisPvm);
    const paattymisPvm = this.dateService.momentToVardaDate(this.filterParams.paattymisPvm);
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
        this.searchResults = response.results.map(toimipaikka => ({
            id: toimipaikka.id,
            textPrimary: toimipaikka.nimi_original,
            textSecondary: this.getSecondaryText(toimipaikka.paos_organisaatio_nimi)
          }));
      });
  }

  filter(): boolean {
    this.isFilters2Active = this.isFilters2Filled();
    if (!this.isFilters1Active && this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI) {
      this.fillFilters1();
    } else if (this.filterParams.voimassaolo === this.voimassaolo.KAIKKI) {
      this.clearFilters1();
      this.isFilters1Active = false;
    } else if (!this.isFilters1Filled()) {
      return false;
    }
    return true;
  }

  fillFilters1() {
    this.filterParams.alkamisPvm = moment();
    this.filterParams.paattymisPvm = moment();
    this.isFilters1Active = false;
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

  isFilters1Filled(): boolean {
    return this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI && this.filterParams.alkamisPvm !== null &&
      this.filterParams.paattymisPvm !== null;
  }

  isFilters2Filled(): boolean {
    return this.filterParams.jarjestamismuoto !== null || this.filterParams.toimintamuoto !== null;
  }

  updateFilterString() {
    const stringParams: Array<FilterStringParam> = [];

    if (this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI) {
      stringParams.push({ value: this.filterParams.voimassaolo, type: FilterStringType.TRANSLATED_STRING });
      if (this.filterParams.alkamisPvm && this.filterParams.paattymisPvm) {
        stringParams.push({ value: 'aikavali', type: FilterStringType.TRANSLATED_STRING, lowercase: true });
        stringParams.push({
          value: `${this.filterParams.alkamisPvm.format(VardaDateService.vardaDefaultDateFormat)} -
        ${this.filterParams.paattymisPvm.format(VardaDateService.vardaDefaultDateFormat)}`,
          type: FilterStringType.RAW,
          ignoreComma: true
        });
      }
    }

    stringParams.push({ value: this.getCodeUiString(this.filterParams.toimintamuoto), type: FilterStringType.RAW, lowercase: true });
    stringParams.push({ value: this.getCodeUiString(this.filterParams.jarjestamismuoto), type: FilterStringType.RAW, lowercase: true });

    setTimeout(() => {
      this.filterString = this.getFilterString(stringParams);
    });
  }
}
