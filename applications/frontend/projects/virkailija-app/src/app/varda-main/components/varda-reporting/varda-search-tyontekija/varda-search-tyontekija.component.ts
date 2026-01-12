import { Component, OnInit } from '@angular/core';
import { BehaviorSubject, forkJoin } from 'rxjs';
import { CodeDTO, KoodistoDTO, VardaKoodistoService, VardaDateService } from 'varda-shared';
import { FilterStringParam, FilterStringType, VardaSearchAbstractComponent } from '../varda-search-abstract.component';
import { BreakpointObserver } from '@angular/cdk/layout';
import { TranslateService } from '@ngx-translate/core';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { DateTime } from 'luxon';
import { AuthService } from '../../../../core/auth/auth.service';
import { PaginatorParams } from '../varda-result-list/varda-result-list.component';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';
import { ViewAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { extractCursor } from "../../../../utilities/helper-functions";

@Component({
    selector: 'app-varda-search-tyontekija',
    templateUrl: './varda-search-tyontekija.component.html',
    styleUrls: ['./varda-search-tyontekija.component.css'],
    standalone: false
})
export class VardaSearchTyontekijaComponent extends VardaSearchAbstractComponent implements OnInit {
  rajaus = {
    PALVELUSSUHTEET: 'palvelussuhteet',
    TYOSKENTELYPAIKAT: 'tyoskentelypaikat',
    POISSAOLOT: 'poissaolot',
    TAYDENNYSKOULUTUKSET: 'taydennyskoulutukset',
    NONE: null
  };

  voimassaolo = {
    ALKANUT: 'alkanut',
    PAATTYNYT: 'paattynyt',
    VOIMASSA: 'voimassa',
  };

  filterParams: {
    aktiiviset: boolean;
    rajaus: string;
    voimassaolo: string;
    alkamisPvm: DateTime;
    paattymisPvm: DateTime;
    tehtavanimike: CodeDTO;
    tutkinto: CodeDTO;
    tehtavanimikeTaydennyskoulutus: CodeDTO;
    kiertava: boolean;
    tyosuhde: CodeDTO;
  } = {
    aktiiviset: true,
    rajaus: null,
    voimassaolo: null,
    alkamisPvm: DateTime.now(),
    paattymisPvm: DateTime.now(),
    tehtavanimike: null,
    tutkinto: null,
    tehtavanimikeTaydennyskoulutus: null,
    kiertava: false,
    tyosuhde: null
  };
  rajausPrevious = this.filterParams.rajaus;
  aktiivisetPrevious = this.filterParams.aktiiviset;

  tehtavanimikkeet: Array<CodeDTO> = [];
  filteredTehtavanimikeOptions: BehaviorSubject<Array<CodeDTO>> = new BehaviorSubject([]);

  tutkinnot: Array<CodeDTO> = [];
  filteredTutkintoOptions: BehaviorSubject<Array<CodeDTO>> = new BehaviorSubject([]);

  tyosuhteet: Array<CodeDTO> = [];

  isVakajarjestajaTyontekijaPermission = false;

  constructor(
    koodistoService: VardaKoodistoService,
    breakpointObserver: BreakpointObserver,
    translateService: TranslateService,
    koosteService: VardaKoosteApiService,
    authService: AuthService,
    vakajarjestajaService: VardaVakajarjestajaService,
    private dateService: VardaDateService
  ) {
    super(koodistoService, breakpointObserver, translateService, koosteService, authService, vakajarjestajaService);
  }

  ngOnInit(): void {
    super.ngOnInit();
    this.toimipaikat = this.authService.getAuthorizedToimipaikat(this.katselijaToimipaikat, ViewAccess.henkilostotiedot);
    this.filteredToimipaikkaOptions.next(this.toimipaikat);
    this.search();
    forkJoin([
      this.getKoodistoFromKoodistoService(this.koodistoEnum.tehtavanimike),
      this.getKoodistoFromKoodistoService(this.koodistoEnum.tutkinto),
      this.getKoodistoFromKoodistoService(this.koodistoEnum.tyosuhde)
    ]).subscribe((data: Array<KoodistoDTO>) => {
      this.tehtavanimikkeet = data[0].codes;
      this.filteredTehtavanimikeOptions.next(this.tehtavanimikkeet);
      this.tutkinnot = data[1].codes;
      this.filteredTutkintoOptions.next(this.tutkinnot);
      this.tyosuhteet = data[2].codes;
    });
    this.isVakajarjestajaTyontekijaPermission = this.authService.getUserAccess().tyontekijatiedot.katselija;
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

    searchParams.search = this.searchValue ? this.searchValue : '';

    if (this.isFilters1Filled()) {
      searchParams.rajaus = this.filterParams.rajaus;
      searchParams.voimassaolo = this.filterParams.voimassaolo;
      searchParams.alkamis_pvm = this.dateService.luxonToVardaDate(this.filterParams.alkamisPvm);
      searchParams.paattymis_pvm = this.dateService.luxonToVardaDate(this.filterParams.paattymisPvm);

      if (this.filterParams.rajaus === this.rajaus.TAYDENNYSKOULUTUKSET &&
        this.filterParams.tehtavanimikeTaydennyskoulutus) {
        searchParams.tehtavanimike_taydennyskoulutus = this.filterParams.tehtavanimikeTaydennyskoulutus.code_value;
      }
    }

    if (this.isFilters3Filled()) {
      searchParams.aktiiviset = true;
      searchParams.alkamis_pvm = this.dateService.luxonToVardaDate(this.filterParams.alkamisPvm);
      searchParams.paattymis_pvm = this.dateService.luxonToVardaDate(this.filterParams.paattymisPvm);
    }

    if (this.filterParams.rajaus !== this.rajaus.TAYDENNYSKOULUTUKSET && this.filterParams.tehtavanimike !== null) {
      searchParams.tehtavanimike = this.filterParams.tehtavanimike.code_value;
    }

    if (this.filterParams.tutkinto !== null) {
      searchParams.tutkinto = this.filterParams.tutkinto.code_value;
    }

    if (this.filterParams.kiertava) {
      searchParams.kiertava = true;
    }

    if (!this.isAllToimipaikatSelected && !this.filterParams.kiertava) {
      searchParams.toimipaikat = this.selectedToimipaikat.map(toimipaikka => toimipaikka.id).join(',');
    }

    if (this.filterParams.tyosuhde) {
      searchParams.tyosuhde = this.filterParams.tyosuhde.code_value;
    }

    this.updateFilterString();

    if (!paginatorParams && this.resultListComponent) {
      this.resultListComponent.resetResults();
    }

    this.koosteService.getTyontekijatForVakajarjestaja(this.selectedVakajarjestaja.id, searchParams).subscribe(response => {
      this.resultCount = response.count;
      this.nextCursor = extractCursor(response.next);
      this.prevCursor = extractCursor(response.previous);
      this.searchResults = response.results.map(tyontekija => ({
          id: tyontekija.tyontekija_id,
          textPrimary: `${tyontekija.sukunimi}, ${tyontekija.etunimet}`,
          textSecondary: null
        }));
    });
  }

  filter(): boolean {
    if (this.rajausPrevious === this.rajaus.NONE && this.filterParams.rajaus !== this.rajaus.NONE) {
      // clear aktiiviset filter
      this.clearFilters3();
      // initialize rajaus filters
      this.fillFilters1();
    } else if (this.aktiivisetPrevious === false && this.filterParams.aktiiviset === true) {
      // clear rajaus filters
      this.clearFilters1();
      // initialize aktiiviset filter
      this.fillFilters3();
    }
    this.rajausPrevious = this.filterParams.rajaus;
    this.aktiivisetPrevious = this.filterParams.aktiiviset;

    if ((this.filterParams.rajaus !== this.rajaus.NONE && !this.isFilters1Filled()) ||
      (this.filterParams.aktiiviset === true && !this.isFilters3Filled())) {
      // rajaus or aktiiviset filters are in use but not all filters are valid, do not continue search
      return false;
    }

    return true;
  }

  isFiltersActive(): boolean {
    return this.filterParams.rajaus !== this.rajaus.NONE || this.filterParams.aktiiviset || this.isFilters2Filled();
  }

  fillFilters1() {
    this.filterParams.voimassaolo = this.voimassaolo.VOIMASSA;
    this.filterParams.alkamisPvm = DateTime.now();
    this.filterParams.paattymisPvm = DateTime.now();
  }

  fillFilters2() {}

  fillFilters3() {
    this.filterParams.aktiiviset = true;
    this.filterParams.alkamisPvm = DateTime.now();
    this.filterParams.paattymisPvm = DateTime.now();
  }

  clearFilters1() {
    this.filterParams.rajaus = this.rajaus.NONE;
    this.filterParams.voimassaolo = null;
    this.filterParams.alkamisPvm = null;
    this.filterParams.paattymisPvm = null;
    this.filterParams.tehtavanimikeTaydennyskoulutus = null;
  }

  clearFilters2() {
    this.filterParams.tehtavanimike = null;
    this.filterParams.tutkinto = null;
    this.filterParams.tyosuhde = null;
  }

  clearFilters3() {
    this.filterParams.aktiiviset = false;
    this.filterParams.alkamisPvm = null;
    this.filterParams.paattymisPvm = null;
  }

  isFilters1Filled(): boolean {
    return this.filterParams.rajaus !== this.rajaus.NONE &&
      this.filterParams.voimassaolo !== null && this.filterParams.alkamisPvm !== null &&
      this.filterParams.paattymisPvm !== null;
  }

  isFilters2Filled(): boolean {
    return this.filterParams.tehtavanimike !== null || this.filterParams.tutkinto !== null ||
      this.filterParams.tyosuhde !== null;
  }

  isFilters3Filled(): boolean {
    return this.filterParams.aktiiviset && this.filterParams.alkamisPvm !== null &&
      this.filterParams.paattymisPvm !== null;
  }

  updateFilterString() {
    const stringParams: Array<FilterStringParam> = [];

    if (this.isFilters1Filled()) {
      stringParams.push({ value: this.filterParams.rajaus, type: FilterStringType.TRANSLATED_STRING });
      if (this.filterParams.rajaus !== this.rajaus.TAYDENNYSKOULUTUKSET) {
        stringParams.push({ value: this.filterParams.voimassaolo, type: FilterStringType.TRANSLATED_STRING, lowercase: true });
      } else {
        stringParams.push(
          { value: this.getCodeUiString(this.filterParams.tehtavanimikeTaydennyskoulutus), type: FilterStringType.RAW, lowercase: true }
        );
      }

      this.addDateRangeFilterString(stringParams);
    }

    if (this.isFilters3Filled()) {
      stringParams.push({ value: this.i18n.katsele_tietoja_tyontekija_active, type: FilterStringType.TRANSLATED_STRING,
        lowercase: true });

      this.addDateRangeFilterString(stringParams);
    }

    if (this.filterParams.rajaus !== this.rajaus.TAYDENNYSKOULUTUKSET) {
      stringParams.push({ value: this.getCodeUiString(this.filterParams.tehtavanimike), type: FilterStringType.RAW, lowercase: true });
    }
    stringParams.push({ value: this.getCodeUiString(this.filterParams.tutkinto), type: FilterStringType.RAW, lowercase: true });
    stringParams.push({ value: this.filterParams.tyosuhde?.name, type: FilterStringType.RAW, lowercase: true });

    setTimeout(() => {
      this.filterString = this.getFilterString(stringParams);
    });
  }

  autofillOnChange() {
    this.search();
  }

  afterUserAccessInit() {
    if (!this.userAccess.tyontekijatiedot.katselija && this.userAccess.taydennyskoulutustiedot.katselija) {
      this.filterParams.rajaus = this.rajaus.TAYDENNYSKOULUTUKSET;
    }
  }
}
