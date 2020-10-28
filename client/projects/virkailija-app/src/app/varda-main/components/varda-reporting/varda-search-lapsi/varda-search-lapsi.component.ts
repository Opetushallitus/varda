import { Component, OnInit } from '@angular/core';
import {
  FilterStringParam,
  FilterStringType,
  VardaSearchAbstractComponent
} from '../varda-search-abstract.component';
import { VardaKoodistoService } from 'varda-shared';
import { BreakpointObserver } from '@angular/cdk/layout';
import { TranslateService } from '@ngx-translate/core';
import { Moment } from 'moment';
import * as moment from 'moment';
import { VardaDateService } from '../../../services/varda-date.service';
import { VardaApiWrapperService } from '../../../../core/services/varda-api-wrapper.service';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { PaginatorParams } from '../varda-result-list/varda-result-list.component';

@Component({
  selector: 'app-varda-search-lapsi',
  templateUrl: './varda-search-lapsi.component.html',
  styleUrls: ['./varda-search-lapsi.component.css']
})
export class VardaSearchLapsiComponent extends VardaSearchAbstractComponent implements OnInit {
  rajaus = {
    VAKASUHTEET: 'vakasuhteet',
    VAKAPAATOKSET: 'vakapaatokset',
    MAKSUTIEDOT: 'maksutiedot',
    NONE: null
  };

  voimassaolo = {
    ALKANUT: 'alkanut',
    PAATTYNYT: 'paattynyt',
    VOIMASSA: 'voimassa',
  };

  filterParams: {
    rajaus: string;
    voimassaolo: string;
    alkamisPvm: Moment;
    paattymisPvm: Moment;
  } = {
    rajaus: this.rajaus.VAKAPAATOKSET,
    voimassaolo: this.voimassaolo.VOIMASSA,
    alkamisPvm: moment(),
    paattymisPvm: moment()
  };

  constructor(
    koodistoService: VardaKoodistoService,
    breakpointObserver: BreakpointObserver,
    translateService: TranslateService,
    authService: AuthService,
    vakajarjestajaService: VardaVakajarjestajaService,
    private dateService: VardaDateService,
    private apiWrapperService: VardaApiWrapperService
  ) {
    super(koodistoService, breakpointObserver, translateService, authService, vakajarjestajaService);
  }

  ngOnInit() {
    super.ngOnInit();
    this.toimipaikat = this.authService.getToimipaikatWithLapsiPermissions(this.katselijaToimipaikat);
    this.filteredToimipaikkaOptions.next(this.toimipaikat);
    this.search();
  }

  search(paginatorParams?: PaginatorParams): void {
    const continueSearch = this.filter();
    if (!continueSearch) {
      return;
    }

    if (!this.isAllToimipaikatSelected && this.selectedToimipaikat.length === 0) {
      return;
    }

    const searchParams = {};
    this.setPaginatorParams(searchParams, paginatorParams);

    const searchVal = this.searchValue;
    searchParams['search'] = searchVal ? searchVal : '';

    if (this.isFiltersFilled()) {
      searchParams['rajaus'] = this.filterParams.rajaus;
      searchParams['voimassaolo'] = this.filterParams.voimassaolo;
      searchParams['alkamis_pvm'] = this.dateService.momentToVardaDate(this.filterParams.alkamisPvm);
      searchParams['paattymis_pvm'] = this.dateService.momentToVardaDate(this.filterParams.paattymisPvm);
    }

    if (!this.isAllToimipaikatSelected) {
      searchParams['toimipaikat'] = this.selectedToimipaikat.map(toimipaikka => toimipaikka.id).join(',');
    }

    this.updateFilterString();

    if (!paginatorParams && this.resultListComponent) {
      this.resultListComponent.resetResults();
    }

    this.apiWrapperService.getLapsetForVakajarjestaja(searchParams).subscribe(response => {
      this.resultCount = response.count;
      this.searchResults = response.results.map(lapsi => {
        return {
          id: lapsi.lapsi_id,
          textPrimary: `${lapsi.sukunimi}, ${lapsi.etunimet}`,
          textSecondary: this.getSecondaryText(lapsi.oma_organisaatio_nimi)
        };
      });
    });
  }

  private filter(): boolean {
    if (this.isFiltersInactive) {
      this.isFiltersInactive = false;
      this.fillFilters();
    }

    if (this.filterParams.rajaus === this.rajaus.NONE) {
      this.isFiltersInactive = true;
      this.clearRajausFilters();
    } else if (!this.isFiltersFilled()) {
      return false;
    }
    return true;
  }

  fillFilters() {
    this.filterParams.voimassaolo = this.voimassaolo.VOIMASSA;
    this.filterParams.alkamisPvm = moment();
    this.filterParams.paattymisPvm = moment();
  }

  updateFilterString() {
    const stringParams: Array<FilterStringParam> = [];

    stringParams.push({value: this.filterParams.rajaus, type: FilterStringType.TRANSLATED_STRING});
    stringParams.push({value: this.filterParams.voimassaolo, type: FilterStringType.TRANSLATED_STRING, lowercase: true});
    if (this.filterParams.alkamisPvm && this.filterParams.paattymisPvm) {
      stringParams.push({value: 'aikavali', type: FilterStringType.TRANSLATED_STRING, lowercase: true});
      stringParams.push({
        value: `${this.filterParams.alkamisPvm.format(VardaDateService.vardaDefaultDateFormat)} -
        ${this.filterParams.paattymisPvm.format(VardaDateService.vardaDefaultDateFormat)}`,
        type: FilterStringType.RAW,
        ignoreComma: true
      });
    }

    setTimeout(() => {
      this.filterString = this.getFilterString(stringParams);
    });
  }

  clearFilters() {
    this.clearRajausFilters();
    this.isFiltersInactive = true;
    this.search();
  }

  clearRajausFilters() {
    this.filterParams.rajaus = this.rajaus.NONE;
    this.filterParams.voimassaolo = null;
    this.filterParams.alkamisPvm = null;
    this.filterParams.paattymisPvm = null;
  }

  isFiltersFilled(): boolean {
    return this.filterParams.rajaus !== this.rajaus.NONE && this.filterParams.rajaus !== null &&
      this.filterParams.voimassaolo !== null && this.filterParams.alkamisPvm !== null &&
      this.filterParams.paattymisPvm !== null;
  }
}
