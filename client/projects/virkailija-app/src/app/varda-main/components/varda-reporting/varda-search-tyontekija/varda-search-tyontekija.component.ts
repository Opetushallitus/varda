import { Component, OnInit } from '@angular/core';
import { BehaviorSubject, forkJoin } from 'rxjs';
import { CodeDTO, KoodistoDTO, VardaKoodistoService } from 'varda-shared';
import {
  FilterStringParam,
  FilterStringType,
  VardaSearchAbstractComponent
} from '../varda-search-abstract.component';
import { BreakpointObserver } from '@angular/cdk/layout';
import { TranslateService } from '@ngx-translate/core';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { Moment } from 'moment';
import * as moment from 'moment';
import { VardaDateService } from '../../../services/varda-date.service';
import { VardaApiWrapperService } from '../../../../core/services/varda-api-wrapper.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { PaginatorParams } from '../varda-result-list/varda-result-list.component';

@Component({
  selector: 'app-varda-search-tyontekija',
  templateUrl: './varda-search-tyontekija.component.html',
  styleUrls: ['./varda-search-tyontekija.component.css']
})
export class VardaSearchTyontekijaComponent extends VardaSearchAbstractComponent implements OnInit {
  rajaus = {
    PALVELUSSUHTEET: 'palvelussuhteet',
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
    tehtavanimike: CodeDTO;
    tutkinto: CodeDTO;
  } = {
    rajaus: this.rajaus.PALVELUSSUHTEET,
    voimassaolo: this.voimassaolo.VOIMASSA,
    alkamisPvm: moment(),
    paattymisPvm: moment(),
    tehtavanimike: null,
    tutkinto: null
  };

  isRajausFiltersInactive = false;

  tehtavanimikkeet: Array<CodeDTO> = [];
  filteredTehtavanimikeOptions: BehaviorSubject<Array<CodeDTO>> = new BehaviorSubject([]);

  tutkinnot: Array<CodeDTO> = [];
  filteredTutkintoOptions: BehaviorSubject<Array<CodeDTO>> = new BehaviorSubject([]);

  constructor(
    koodistoService: VardaKoodistoService,
    breakpointObserver: BreakpointObserver,
    translateService: TranslateService,
    authService: AuthService,
    vakajarjestajaService: VardaVakajarjestajaService,
    private apiWrapperService: VardaApiWrapperService,
    private dateService: VardaDateService
  ) {
    super(koodistoService, breakpointObserver, translateService, authService, vakajarjestajaService);
  }

  ngOnInit(): void {
    super.ngOnInit();
    this.toimipaikat = this.authService.getToimipaikatWithTyontekijaPermissions(this.katselijaToimipaikat);
    this.filteredToimipaikkaOptions.next(this.toimipaikat);
    this.search();
    forkJoin([
      this.getKoodistoFromKoodistoService(this.koodistoEnum.tehtavanimike),
      this.getKoodistoFromKoodistoService(this.koodistoEnum.tutkinto)
    ]).subscribe(data => {
      this.tehtavanimikkeet = (<KoodistoDTO>data[0]).codes;
      this.filteredTehtavanimikeOptions.next(this.tehtavanimikkeet);
      this.tutkinnot = (<KoodistoDTO>data[1]).codes;
      this.filteredTutkintoOptions.next(this.tutkinnot);
    });
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

    this.isFiltersInactive = !this.isFiltersFilled();

    searchParams['search'] = this.searchValue ? this.searchValue : '';

    if (this.isRajausFiltersFilled()) {
      searchParams['rajaus'] = this.filterParams.rajaus;
      searchParams['voimassaolo'] = this.filterParams.voimassaolo;
      searchParams['alkamis_pvm'] = this.dateService.momentToVardaDate(this.filterParams.alkamisPvm);
      searchParams['paattymis_pvm'] = this.dateService.momentToVardaDate(this.filterParams.paattymisPvm);
    }
    if (this.filterParams.tehtavanimike !== null) {
      searchParams['tehtavanimike'] = this.filterParams.tehtavanimike.code_value;
    }
    if (this.filterParams.tutkinto !== null) {
      searchParams['tutkinto'] = this.filterParams.tutkinto.code_value;
    }

    if (!this.isAllToimipaikatSelected) {
      searchParams['toimipaikat'] = this.selectedToimipaikat.map(toimipaikka => toimipaikka.id).join(',');
    }

    this.updateFilterString();

    if (!paginatorParams && this.resultListComponent) {
      this.resultListComponent.resetResults();
    }

    this.apiWrapperService.getTyontekijatForVakajarjestaja(searchParams).subscribe(response => {
      this.resultCount = response.count;
      this.searchResults = response.results.map(tyontekija => {
        return {
          id: tyontekija.tyontekija_id,
          textPrimary: `${tyontekija.sukunimi}, ${tyontekija.etunimet}`,
          textSecondary: null
        };
      });
    });
  }

  private filter(): boolean {
    if (this.isRajausFiltersInactive) {
      this.isRajausFiltersInactive = false;
      this.fillRajausFilter();
    }

    if (this.filterParams.rajaus === this.rajaus.NONE) {
      this.isRajausFiltersInactive = true;
      this.clearRajausFilter();
    } else if (!this.isFiltersFilled()) {
      return false;
    }
    return true;
  }

  fillRajausFilter() {
    this.filterParams.voimassaolo = this.voimassaolo.VOIMASSA;
    this.filterParams.alkamisPvm = moment();
    this.filterParams.paattymisPvm = moment();
  }

  clearRajausFilter() {
    this.filterParams.rajaus = this.rajaus.NONE;
    this.filterParams.voimassaolo = null;
    this.filterParams.alkamisPvm = null;
    this.filterParams.paattymisPvm = null;
    this.isRajausFiltersInactive = true;
  }

  clearFilters() {
    this.filterParams.tehtavanimike = null;
    this.filterParams.tutkinto = null;
    this.isFiltersInactive = true;
    this.clearRajausFilter();
    this.search();
  }

  isFiltersFilled(): boolean {
    return this.isRajausFiltersFilled() || (this.filterParams.rajaus === this.rajaus.NONE &&
      (this.filterParams.tehtavanimike !== null || this.filterParams.tutkinto !== null));
  }

  isRajausFiltersFilled(): boolean {
    return this.filterParams.rajaus !== this.rajaus.NONE &&
      this.filterParams.voimassaolo !== null && this.filterParams.alkamisPvm !== null &&
      this.filterParams.paattymisPvm !== null;
  }

  updateFilterString() {
    const stringParams: Array<FilterStringParam> = [];

    if (this.isRajausFiltersFilled()) {
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
    }

    stringParams.push({value: this.filterParams.tehtavanimike?.code_value, type: FilterStringType.RAW});
    stringParams.push({value: this.filterParams.tutkinto?.code_value, type: FilterStringType.RAW});

    setTimeout(() => {
      this.filterString = this.getFilterString(stringParams);
    });
  }

  tehtavanimikeOnChange(tehtavanimike: CodeDTO) {
    this.search();
  }

  tutkintoOnChange(tutkinto: CodeDTO) {
    this.search();
  }
}
