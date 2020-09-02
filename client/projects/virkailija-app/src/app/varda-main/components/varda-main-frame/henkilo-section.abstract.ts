import { OnChanges, Input, Output, EventEmitter, SimpleChanges, OnDestroy, Component } from '@angular/core';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { BehaviorSubject, Subscription } from 'rxjs';
import { PageEvent } from '@angular/material/paginator';
import { HenkiloListDTO } from '../../../utilities/models/dto/varda-henkilo-dto.model';
import { LapsiListDTO } from '../../../utilities/models/dto/varda-lapsi-dto.model';
import { TyontekijaListDTO } from '../../../utilities/models/dto/varda-tyontekija-dto.model';
import { VardaApiService } from 'projects/virkailija-app/src/app/core/services/varda-api.service';

export interface HenkiloSearchFilter {
  previousSearch?: string;
  page: number;
  page_size: number;
  search?: string;
  count?: number;
  kiertava_tyontekija_kytkin?: boolean;
  toimipaikka_oid?: string;
  toimipaikka_id?: string;
}

@Component({
  template: ''
})
export abstract class AbstractHenkiloSectionComponent implements OnChanges, OnDestroy {
  @Input() selectedToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() toimipaikkaAccess: UserAccess;
  @Output() openHenkiloForm = new EventEmitter<LapsiListDTO | TyontekijaListDTO>(true);

  subscriptions: Array<Subscription> = [];
  henkilot: Array<HenkiloListDTO>;
  showFilters: boolean;
  isLoading = new BehaviorSubject<boolean>(false);
  searchFilter: HenkiloSearchFilter = {
    page_size: 20,
    page: 1,
    count: 0
  };

  constructor(private vardaApiService: VardaApiService) { }

  ngOnChanges(change: SimpleChanges) {
    this.henkilot = null;

    if (change.selectedToimipaikka) {
      this.searchFilter.page = 1;
      this.searchFilter.toimipaikka_id = change.selectedToimipaikka.currentValue?.id || '';
      this.getHenkilot();
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }

  getFilter(): HenkiloSearchFilter {
    const cleanSearchFilter: HenkiloSearchFilter = {
      page: null,
      page_size: null,
    };

    for (const [key, value] of Object.entries(this.searchFilter)) {
      if (value) {
        cleanSearchFilter[key] = key === 'search' ? this.vardaApiService.hashHetu(value) : value;
      }
    }

    return cleanSearchFilter;
  }

  searchHenkilot(pageEvent?: PageEvent) {
    if (pageEvent) {
      this.searchFilter.page = pageEvent.pageIndex + 1;
      this.searchFilter.page_size = pageEvent.pageSize;
    } else {
      this.searchFilter.page = 1;
    }

    this.getHenkilot();
  }

  abstract getHenkilot(): void;
  abstract addHenkilo(): void;
  abstract openHenkilo(suhde: LapsiListDTO | TyontekijaListDTO): void;

}
