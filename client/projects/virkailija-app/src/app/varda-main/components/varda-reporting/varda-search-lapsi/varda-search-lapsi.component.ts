import { Component, OnInit } from '@angular/core';
import { FilterStringParam, FilterStringType, VardaSearchAbstractComponent } from '../varda-search-abstract.component';
import { CodeDTO, KoodistoDTO, VardaDateService, VardaKoodistoService } from 'varda-shared';
import { BreakpointObserver } from '@angular/cdk/layout';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { Moment } from 'moment';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { PaginatorParams } from '../varda-result-list/varda-result-list.component';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';
import { ViewAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { forkJoin } from 'rxjs';

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
    maksunPeruste: CodeDTO;
    palveluseteli: boolean;
    jarjestamismuoto: CodeDTO;
    toimintamuoto: CodeDTO;
  } = {
    rajaus: this.rajaus.VAKAPAATOKSET,
    voimassaolo: this.voimassaolo.VOIMASSA,
    alkamisPvm: moment(),
    paattymisPvm: moment(),
    maksunPeruste: null,
    palveluseteli: null,
    jarjestamismuoto: null,
    toimintamuoto: null
  };

  maksunPerusteCodes: Array<CodeDTO> = [];
  jarjestamismuotoCodes: Array<CodeDTO> = [];
  toimintamuotoCodes: Array<CodeDTO> = [];

  constructor(
    koodistoService: VardaKoodistoService,
    breakpointObserver: BreakpointObserver,
    translateService: TranslateService,
    koosteService: VardaKoosteApiService,
    authService: AuthService,
    vakajarjestajaService: VardaVakajarjestajaService,
    private dateService: VardaDateService,
  ) {
    super(koodistoService, breakpointObserver, translateService, koosteService, authService, vakajarjestajaService);
  }

  ngOnInit() {
    super.ngOnInit();
    this.toimipaikat = this.authService.getAuthorizedToimipaikat(this.katselijaToimipaikat, ViewAccess.lapsitiedot);
    this.filteredToimipaikkaOptions.next(this.toimipaikat);
    this.search();
    forkJoin([
      this.getKoodistoFromKoodistoService(this.koodistoEnum.maksunperuste),
      this.getKoodistoFromKoodistoService(this.koodistoEnum.jarjestamismuoto),
      this.getKoodistoFromKoodistoService(this.koodistoEnum.toimintamuoto)
    ]).subscribe((data: Array<KoodistoDTO>) => {
      this.maksunPerusteCodes = data[0].codes;
      this.jarjestamismuotoCodes = data[1].codes;
      this.toimintamuotoCodes = data[2].codes;
    });
  }

  search(paginatorParams?: PaginatorParams): void {
    const continueSearch = this.filter();
    if (!continueSearch) {
      return;
    }

    if (this.searchInput && !this.searchInput.valid) {
      return;
    }

    if (!this.isAllToimipaikatSelected && this.selectedToimipaikat.length === 0) {
      return;
    }

    const searchParams: Record<string, unknown> = {};
    this.setPaginatorParams(searchParams, paginatorParams);

    const searchVal = this.searchValue;
    searchParams.search = searchVal ? searchVal : '';

    if (this.isFilters1Filled()) {
      searchParams.rajaus = this.filterParams.rajaus;
      searchParams.voimassaolo = this.filterParams.voimassaolo;
      searchParams.alkamis_pvm = this.dateService.momentToVardaDate(this.filterParams.alkamisPvm);
      searchParams.paattymis_pvm = this.dateService.momentToVardaDate(this.filterParams.paattymisPvm);

      if (this.filterParams.rajaus === this.rajaus.MAKSUTIEDOT) {
        if (this.filterParams.maksunPeruste) {
          searchParams.maksun_peruste = this.filterParams.maksunPeruste.code_value;
        }
        if (this.filterParams.palveluseteli !== null) {
          searchParams.palveluseteli = this.filterParams.palveluseteli;
        }
      }
    }

    if (this.filterParams.jarjestamismuoto) {
      searchParams.jarjestamismuoto = this.filterParams.jarjestamismuoto.code_value;
    }

    if (this.filterParams.toimintamuoto) {
      searchParams.toimintamuoto = this.filterParams.toimintamuoto.code_value;
    }

    if (!this.isAllToimipaikatSelected) {
      searchParams.toimipaikat = this.selectedToimipaikat.map(toimipaikka => toimipaikka.id).join(',');
    }

    this.updateFilterString();

    if (!paginatorParams && this.resultListComponent) {
      this.resultListComponent.resetResults();
    }

    this.koosteService.getLapsetForVakajarjestaja(this.selectedVakajarjestaja.id, searchParams).subscribe(response => {
      this.resultCount = response.count;
      this.searchResults = response.results.map(lapsi => ({
          id: lapsi.lapsi_id,
          textPrimary: `${lapsi.sukunimi}, ${lapsi.etunimet}`,
          textSecondary: this.getSecondaryText(lapsi.paos_organisaatio_nimi) || this.getSecondaryText(lapsi.oma_organisaatio_nimi)
        }));
    });
  }

  filter(): boolean {
    this.isFilters2Active = this.isFilters2Filled();
    if (!this.isFilters1Active && this.filterParams.rajaus !== this.rajaus.NONE) {
      this.isFilters1Active = true;
      this.fillFilters1();
    }

    if (this.filterParams.rajaus === this.rajaus.NONE) {
      this.clearFilters1();
      this.isFilters1Active = false;
    } else if (!this.isFilters1Filled()) {
      return false;
    }
    return true;
  }

  fillFilters1() {
    this.filterParams.voimassaolo = this.voimassaolo.VOIMASSA;
    this.filterParams.alkamisPvm = moment();
    this.filterParams.paattymisPvm = moment();
  }

  clearFilters1() {
    this.filterParams.rajaus = this.rajaus.NONE;
    this.filterParams.voimassaolo = null;
    this.filterParams.alkamisPvm = null;
    this.filterParams.paattymisPvm = null;
    this.filterParams.maksunPeruste = null;
    this.filterParams.palveluseteli = null;
  }

  clearFilters2() {
    this.filterParams.jarjestamismuoto = null;
  }

  isFilters1Filled(): boolean {
    return this.filterParams.rajaus !== this.rajaus.NONE && this.filterParams.rajaus !== null &&
      this.filterParams.voimassaolo !== null && this.filterParams.alkamisPvm !== null &&
      this.filterParams.paattymisPvm !== null;
  }

  isFilters2Filled(): boolean {
    return this.filterParams.jarjestamismuoto !== null;
  }

  updateFilterString() {
    const stringParams: Array<FilterStringParam> = [];

    if (this.isFilters1Filled()) {
      stringParams.push({ value: this.filterParams.rajaus, type: FilterStringType.TRANSLATED_STRING });
      stringParams.push({ value: this.filterParams.voimassaolo, type: FilterStringType.TRANSLATED_STRING, lowercase: true });
      if (this.filterParams.alkamisPvm && this.filterParams.paattymisPvm) {
        stringParams.push({ value: 'aikavali', type: FilterStringType.TRANSLATED_STRING, lowercase: true });
        stringParams.push({
          value: `${this.filterParams.alkamisPvm.format(VardaDateService.vardaDefaultDateFormat)} -
        ${this.filterParams.paattymisPvm.format(VardaDateService.vardaDefaultDateFormat)}`,
          type: FilterStringType.RAW,
          ignoreComma: true
        });
      }

      if (this.filterParams.rajaus === this.rajaus.MAKSUTIEDOT) {
        stringParams.push({ value: this.getCodeUiString(this.filterParams.maksunPeruste), type: FilterStringType.RAW, lowercase: true });
        if (this.filterParams.palveluseteli !== null) {
          stringParams.push({ value: 'palveluseteli', type: FilterStringType.TRANSLATED_STRING, lowercase: true });
          stringParams.push({ value: ': ', type: FilterStringType.RAW, ignoreComma: true, ignoreSpace: true });
          stringParams.push({ value: this.filterParams.palveluseteli ? 'yes' : 'no',
            type: FilterStringType.TRANSLATED_STRING, lowercase: true, ignoreComma: true });
        }
      }
    }

    stringParams.push({ value: this.getCodeUiString(this.filterParams.jarjestamismuoto), type: FilterStringType.RAW, lowercase: true});

    setTimeout(() => {
      this.filterString = this.getFilterString(stringParams);
    });
  }

  autofillOnChange() {
    this.search();
  }

  afterUserAccessInit() {
    if (!this.userAccess.lapsitiedot.katselija && this.userAccess.huoltajatiedot.katselija) {
      this.filterParams.rajaus = this.rajaus.MAKSUTIEDOT;
    }
  }
}
