import { Component, OnInit } from '@angular/core';
import { BehaviorSubject, forkJoin } from 'rxjs';
import { CodeDTO, KoodistoDTO, VardaKoodistoService, VardaDateService } from 'varda-shared';
import { FilterStringParam, FilterStringType, VardaSearchAbstractComponent } from '../varda-search-abstract.component';
import { BreakpointObserver } from '@angular/cdk/layout';
import { TranslateService } from '@ngx-translate/core';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import * as moment from 'moment';
import { Moment } from 'moment';
import { AuthService } from '../../../../core/auth/auth.service';
import { PaginatorParams } from '../varda-result-list/varda-result-list.component';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';
import { ViewAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';

@Component({
  selector: 'app-varda-search-tyontekija',
  templateUrl: './varda-search-tyontekija.component.html',
  styleUrls: ['./varda-search-tyontekija.component.css']
})
export class VardaSearchTyontekijaComponent extends VardaSearchAbstractComponent implements OnInit {
  rajaus = {
    PALVELUSSUHTEET: 'palvelussuhteet',
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
    rajaus: string;
    voimassaolo: string;
    alkamisPvm: Moment;
    paattymisPvm: Moment;
    tehtavanimike: CodeDTO;
    tutkinto: CodeDTO;
    tehtavanimikeTaydennyskoulutus: CodeDTO;
    kiertava: boolean;
    tyosuhde: CodeDTO;
  } = {
    rajaus: this.rajaus.PALVELUSSUHTEET,
    voimassaolo: this.voimassaolo.VOIMASSA,
    alkamisPvm: moment(),
    paattymisPvm: moment(),
    tehtavanimike: null,
    tutkinto: null,
    tehtavanimikeTaydennyskoulutus: null,
    kiertava: false,
    tyosuhde: null
  };

  isRajausFiltersInactive = false;

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

    if (!this.isAllToimipaikatSelected && this.selectedToimipaikat.length === 0) {
      return;
    }

    const searchParams: Record<string, unknown> = {};
    this.setPaginatorParams(searchParams, paginatorParams);

    this.isFiltersInactive = !this.isFiltersFilled();

    searchParams.search = this.searchValue ? this.searchValue : '';

    if (this.isRajausFiltersFilled()) {
      searchParams.rajaus = this.filterParams.rajaus;
      searchParams.voimassaolo = this.filterParams.voimassaolo;
      searchParams.alkamis_pvm = this.dateService.momentToVardaDate(this.filterParams.alkamisPvm);
      searchParams.paattymis_pvm = this.dateService.momentToVardaDate(this.filterParams.paattymisPvm);

      if (this.filterParams.rajaus === this.rajaus.TAYDENNYSKOULUTUKSET &&
        this.filterParams.tehtavanimikeTaydennyskoulutus) {
        searchParams.tehtavanimike_taydennyskoulutus = this.filterParams.tehtavanimikeTaydennyskoulutus.code_value;
      }
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
      this.searchResults = response.results.map(tyontekija => ({
          id: tyontekija.tyontekija_id,
          textPrimary: `${tyontekija.sukunimi}, ${tyontekija.etunimet}`,
          textSecondary: null
        }));
    });
  }

  filter(): boolean {
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
    this.filterParams.tehtavanimikeTaydennyskoulutus = null;
    this.isRajausFiltersInactive = true;
  }

  clearFilters() {
    this.filterParams.tehtavanimike = null;
    this.filterParams.tutkinto = null;
    this.filterParams.tyosuhde = null;
    this.isFiltersInactive = true;
    this.clearRajausFilter();
    this.search();
  }

  isFiltersFilled(): boolean {
    return this.isRajausFiltersFilled() || (this.filterParams.rajaus === this.rajaus.NONE &&
      (this.filterParams.tehtavanimike !== null || this.filterParams.tutkinto !== null || this.filterParams.tyosuhde !== null));
  }

  isRajausFiltersFilled(): boolean {
    return this.filterParams.rajaus !== this.rajaus.NONE &&
      this.filterParams.voimassaolo !== null && this.filterParams.alkamisPvm !== null &&
      this.filterParams.paattymisPvm !== null;
  }

  updateFilterString() {
    const stringParams: Array<FilterStringParam> = [];

    if (this.isRajausFiltersFilled()) {
      stringParams.push({ value: this.filterParams.rajaus, type: FilterStringType.TRANSLATED_STRING });
      if (this.filterParams.rajaus !== this.rajaus.TAYDENNYSKOULUTUKSET) {
        stringParams.push({ value: this.filterParams.voimassaolo, type: FilterStringType.TRANSLATED_STRING, lowercase: true });
      } else {
        stringParams.push({ value: this.getCodeUiString(this.filterParams.tehtavanimikeTaydennyskoulutus), type: FilterStringType.RAW, lowercase: true });
      }
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
