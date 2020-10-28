import { AfterViewInit, Component, OnInit } from '@angular/core';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import {
  FilterStringParam,
  FilterStringType,
  VardaSearchAbstractComponent
} from '../varda-search-abstract.component';
import { VardaKoodistoService } from 'varda-shared';
import { BreakpointObserver } from '@angular/cdk/layout';
import { TranslateService } from '@ngx-translate/core';
import { VardaApiService } from '../../../../core/services/varda-api.service';
import * as moment from 'moment';
import { AuthService } from '../../../../core/auth/auth.service';
import { PaginatorParams } from '../varda-result-list/varda-result-list.component';

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
    toimintamuoto: string;
    jarjestamismuoto: string;
    voimassaolo: string;
  } = {
    toimintamuoto: '',
    jarjestamismuoto: '',
    voimassaolo: this.voimassaolo.KAIKKI
  };

  constructor(
    koodistoService: VardaKoodistoService,
    breakpointObserver: BreakpointObserver,
    translateService: TranslateService,
    vakajarjestajaService: VardaVakajarjestajaService,
    authService: AuthService,
    private apiService: VardaApiService
  ) {
    super(koodistoService, breakpointObserver, translateService, authService, vakajarjestajaService);
    this.isFiltersInactive = true;
  }

  ngOnInit() {
    super.ngOnInit();
    this.search();
  }

  search(paginatorParams?: PaginatorParams): any {
    const searchParams = {};
    this.setPaginatorParams(searchParams, paginatorParams);

    this.isFiltersInactive = !this.isFiltersFilled();
    this.updateFilterString();

    if (this.searchValue) {
      searchParams['nimi'] = this.searchValue;
    }
    if (this.filterParams.jarjestamismuoto !== '') {
      searchParams['jarjestamismuoto_koodi'] = this.filterParams.jarjestamismuoto.toLowerCase();
    }
    if (this.filterParams.toimintamuoto !== '') {
      searchParams['toimintamuoto_koodi'] = this.filterParams.toimintamuoto.toLowerCase();
    }

    const today = moment().format('YYYY-MM-DD');
    switch (this.filterParams.voimassaolo) {
      case this.voimassaolo.VOIMASSAOLEVAT:
        searchParams['alkamis_pvm_before'] = today;
        searchParams['paattymis_pvm_after'] = today;
        break;
      case this.voimassaolo.PAATTYNEET:
        searchParams['paattymis_pvm_before'] = today;
        break;
    }

    if (!paginatorParams && this.resultListComponent) {
      this.resultListComponent.resetResults();
    }

    this.apiService
      .getToimipaikatForVakaJarjestaja(this.vakajarjestajaService.getSelectedVakajarjestajaId(), searchParams)
      .subscribe(response => {
        this.resultCount = response.count;
        this.searchResults = response.results.map(toimipaikka => {
          return {
            id: toimipaikka.id,
            textPrimary: toimipaikka.nimi_original,
            textSecondary: this.getSecondaryText(toimipaikka.paos_organisaatio_nimi)
          };
        });
      });
  }

  updateFilterString() {
    const stringParams: Array<FilterStringParam> = [];

    if (this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI) {
      stringParams.push({value: this.filterParams.voimassaolo, type: FilterStringType.TRANSLATED_STRING});
    }

    stringParams.push({value: this.filterParams.toimintamuoto, type: FilterStringType.RAW});
    stringParams.push({value: this.filterParams.jarjestamismuoto, type: FilterStringType.RAW});

    setTimeout(() => {
      this.filterString = this.getFilterString(stringParams);
    });
  }

  isFiltersFilled(): boolean {
    return this.filterParams.voimassaolo !== this.voimassaolo.KAIKKI ||
      this.filterParams.jarjestamismuoto !== '' || this.filterParams.toimintamuoto !== '';
  }

  clearFilters(): void {
    this.filterParams.voimassaolo = this.voimassaolo.KAIKKI;
    this.filterParams.toimintamuoto = '';
    this.filterParams.jarjestamismuoto = '';
    this.isFiltersInactive = true;
    this.search();
  }
}
