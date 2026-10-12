import { OnChanges, Input, Output, EventEmitter, SimpleChanges, OnDestroy, Component } from '@angular/core';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { BehaviorSubject, Subscription } from 'rxjs';
import { PageEvent } from '@angular/material/paginator';
import { HenkiloListDTO } from '../../../utilities/models/dto/varda-henkilo-dto.model';
import { LapsiListDTO } from '../../../utilities/models/dto/varda-lapsi-dto.model';
import { TyontekijaListDTO } from '../../../utilities/models/dto/varda-tyontekija-dto.model';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';


export interface HenkiloSearchFilter {
  cursor?: string | null;
  page_size?: number;
  search?: string;
  kiertava_tyontekija_kytkin?: boolean;
  toimipaikka_oid?: string;
  toimipaikka_id?: string;
  voimassa_pvm?: string;
}

@Component({
    template: '',
    standalone: false
})
export abstract class AbstractHenkiloSectionComponent implements OnChanges, OnDestroy {
  @Input() selectedToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() toimipaikkaAccess: UserAccess;
  @Input() resultCount: number;
  @Input() nextCursor: string | null;
  @Input() prevCursor: string | null;
  @Output() openHenkiloForm = new EventEmitter<LapsiListDTO | TyontekijaListDTO>(true);

  currentPageIndex: number = 0;
  subscriptions: Array<Subscription> = [];
  henkilot: Array<HenkiloListDTO>;
  showFilters: boolean;
  isLoading = new BehaviorSubject<boolean>(false);
  searchFilter: HenkiloSearchFilter = {
    cursor: null,
    page_size: 20,
    voimassa_pvm: this.getTodayAsDate()
  };

  constructor(
    private vardaUtilityService: VardaUtilityService
  ) { }

  ngOnChanges(change: SimpleChanges) {
    this.henkilot = null;

    if (change.selectedToimipaikka) {
      delete this.searchFilter.cursor;
      this.searchFilter.toimipaikka_id = change.selectedToimipaikka.currentValue?.id || '';
      this.getHenkilot();
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }

  getFilter(): HenkiloSearchFilter {
    const cleanSearchFilter: HenkiloSearchFilter = {
      page_size: null,
    };

    for (const [key, value] of Object.entries(this.searchFilter)) {
      if (value) {
        cleanSearchFilter[key] = key === 'search' ? this.vardaUtilityService.hashHetu(value) : value;
      }
    }

    return cleanSearchFilter;
  }

  searchHenkilot(pageEvent?: PageEvent) {
    if (pageEvent) {
      this.currentPageIndex = pageEvent.pageIndex;
      this.searchFilter.page_size = pageEvent.pageSize;

      const goingForward =
        pageEvent.previousPageIndex !== null &&
        pageEvent.pageIndex > pageEvent.previousPageIndex;

      if (goingForward) {
        if (this.nextCursor) {
          this.searchFilter.cursor = this.nextCursor;
        }
      } else {
        if (this.prevCursor) {
          this.searchFilter.cursor = this.prevCursor;
        }
      }

    } else {
      delete this.searchFilter.cursor;
      this.currentPageIndex = 0;
    }

    this.getHenkilot();
  }

  toggleAktiiviset() {
    this.searchFilter.voimassa_pvm = this.searchFilter.voimassa_pvm ? null : this.getTodayAsDate();
    this.searchHenkilot();
  }

  getTodayAsDate(): string {
    const today = new Date();
    const offset = today.getTimezoneOffset();
    const localDate = new Date(today.getTime() - (offset * 60 * 1000));
    return localDate.toISOString().split('T')[0];
  }

  abstract getHenkilot(): void;
  abstract addHenkilo(): void;
  abstract openHenkilo(suhde: LapsiListDTO | TyontekijaListDTO): void;

}
