import { Component, OnInit } from '@angular/core';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import {
  FilterStringParam,
  FilterStringType,
  VardaSearchAbstractComponent
} from '../varda-search-abstract.component';
import { CodeDTO, VardaKoodistoService } from 'varda-shared';
import { BreakpointObserver } from '@angular/cdk/layout';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { AuthService } from '../../../../core/auth/auth.service';
import { PaginatorParams } from '../varda-result-list/varda-result-list.component';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';

@Component({
  selector: 'app-varda-search-toimipaikka',
  templateUrl: './varda-search-toimipaikka.component.html',
  styleUrls: ['./varda-search-toimipaikka.component.css']
})
export class VardaSearchToimipaikkaComponent extends VardaSearchAbstractComponent implements OnInit {
  voimassaolo = {
    KAIKKI: 'kaikki',
    VOIMASSAOLEVAT: 'voimassa',
    PAATTYNEET: 'paattynyt'
  };

  filterParams: {
    toimintamuoto: CodeDTO;
    jarjestamismuoto: CodeDTO;
    voimassaolo: string;
  } = {
      toimintamuoto: null,
      jarjestamismuoto: null,
      voimassaolo: this.voimassaolo.KAIKKI
    };

  constructor(
    koodistoService: VardaKoodistoService,
    breakpointObserver: BreakpointObserver,
    translateService: TranslateService,
    koosteService: VardaKoosteApiService,
    vakajarjestajaService: VardaVakajarjestajaService,
    authService: AuthService
  ) {
    super(koodistoService, breakpointObserver, translateService, koosteService, authService, vakajarjestajaService);
    this.isFiltersInactive = true;
  }

  ngOnInit() {
    super.ngOnInit();
    this.search();
  }

  search(paginatorParams?: PaginatorParams): any {
    if (this.searchInput && !this.searchInput.valid) {
      return;
    }

    const searchParams: Record<string, unknown> = {};
    this.setPaginatorParams(searchParams, paginatorParams);

    this.isFiltersInactive = !this.isFiltersFilled();
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

    const today = moment().format('YYYY-MM-DD');
    switch (this.filterParams.voimassaolo) {
      case this.voimassaolo.VOIMASSAOLEVAT:
        searchParams.alkamis_pvm_before = today;
        searchParams.paattymis_pvm_after = today;
        break;
      case this.voimassaolo.PAATTYNEET:
        searchParams.paattymis_pvm_before = today;
        break;
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

  updateFilterString() {
    const stringParams: Array<FilterStringParam> = [];

    if (this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI) {
      stringParams.push({ value: this.filterParams.voimassaolo, type: FilterStringType.TRANSLATED_STRING });
    }

    stringParams.push({ value: this.getCodeUiString(this.filterParams.toimintamuoto), type: FilterStringType.RAW, lowercase: true });
    stringParams.push({ value: this.getCodeUiString(this.filterParams.jarjestamismuoto), type: FilterStringType.RAW, lowercase: true });

    setTimeout(() => {
      this.filterString = this.getFilterString(stringParams);
    });
  }

  isFiltersFilled(): boolean {
    return this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI ||
      this.filterParams.jarjestamismuoto !== null || this.filterParams.toimintamuoto !== null;
  }

  clearFilters(): void {
    this.filterParams.voimassaolo = this.voimassaolo.KAIKKI;
    this.filterParams.toimintamuoto = null;
    this.filterParams.jarjestamismuoto = null;
    this.isFiltersInactive = true;
    this.search();
  }
}
