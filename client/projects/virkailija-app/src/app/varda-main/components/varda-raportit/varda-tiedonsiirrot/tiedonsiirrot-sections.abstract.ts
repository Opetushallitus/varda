import { OnDestroy, Component, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { ActivatedRoute } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Moment } from 'moment';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { ErrorTree, HenkilostoErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Subscription, BehaviorSubject, Observable } from 'rxjs';
import { KoodistoEnum } from 'varda-shared';
import { VardaDateService } from '../../../services/varda-date.service';



export interface TiedonsiirrotSearchFilter {
  page: number;
  page_size: number;
  search?: string;
  vakajarjestajat?: Array<number>;
  successful?: boolean;
  timestamp_after?: string | Moment;
  timestamp_before?: string | Moment;
  request_url?: string;
  request_method?: string;
  request_body?: string;
  response_body?: string;
  response_code?: string;
  lahdejarjestelma?: number;
  username?: string;
  search_target?: string;
}

export interface TiedonsiirrotColumnFields {
  key: string;
  name: string;
  selected?: boolean;
  disabled?: boolean;
}

@Component({
  template: ''
})
export abstract class AbstractTiedonsiirrotSectionsComponent implements OnInit, OnDestroy {
  protected errorService: HenkilostoErrorMessageService;
  abstract columnFields: Array<TiedonsiirrotColumnFields>;
  isLoading = new BehaviorSubject<boolean>(true);
  toimijaAccess: UserAccess;
  i18n = VirkailijaTranslations;
  subscriptions: Array<Subscription> = [];
  formErrors: Observable<Array<ErrorTree>>;
  displayedColumns: Array<string>;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  vakajarjestajat$: Observable<Array<VardaVakajarjestajaUi>>;
  koodistoEnum = KoodistoEnum;
  resultCount = 0;

  searchFilter: TiedonsiirrotSearchFilter = {
    page_size: 20,
    page: 1,
    vakajarjestajat: [],
    successful: null,
    timestamp_after: null,
    timestamp_before: null,
    request_url: null,
    request_method: null,
    request_body: null,
    response_body: null,
    response_code: null,
    lahdejarjestelma: null,
    username: null,
    search_target: null,
  };

  constructor(
    protected authService: AuthService,
    protected translateService: TranslateService,
    protected route: ActivatedRoute,
    protected vakajarjestajaService: VardaVakajarjestajaService,
    protected raportitService: VardaRaportitService
  ) {
    this.errorService = new HenkilostoErrorMessageService(this.translateService);
    this.formErrors = this.errorService.initErrorList();

    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    this.toimijaAccess = this.authService.getUserAccess();
  }

  ngOnInit() {
    this.displayedColumns = this.displayedColumns || this.columnFields.map(field => field.key);

    this.subscriptions.push(
      this.raportitService.getSelectedVakajarjestajat().subscribe(selectedVakajarjestajat => {
        this.searchFilter.vakajarjestajat = selectedVakajarjestajat || [this.selectedVakajarjestaja.id];
        this.getPage(true);
      })
    );
  }


  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }

  changePage(pageEvent: PageEvent) {
    this.searchFilter.page = pageEvent.pageIndex + 1;
    this.searchFilter.page_size = pageEvent.pageSize;


    this.getPage();
  }

  toggleColumn() {
    this.isLoading.next(true);
    setTimeout(() => {
      const columns = this.columnFields.filter(field => field.selected).map(field => field.key);
      this.displayedColumns = columns;
      this.isLoading.next(false);
    }, 500);
  }

  getSearchFilter(): TiedonsiirrotSearchFilter {
    const returnFilter: TiedonsiirrotSearchFilter = {
      page_size: 20,
      page: 1,
    };

    Object.entries(this.searchFilter).filter(([key, value]) => typeof value === 'boolean' || value)
      .forEach(([key, value]) => returnFilter[key] = Array.isArray(value) ? value.join(',') : value);

    if (returnFilter.timestamp_after) {
      returnFilter.timestamp_after = (returnFilter.timestamp_after as Moment).format(`${VardaDateService.vardaApiDateFormat}T00:00:00`);
    }

    if (returnFilter.timestamp_before) {
      returnFilter.timestamp_before = (returnFilter.timestamp_before as Moment).format(`${VardaDateService.vardaApiDateFormat}T23:59:59`);
    }


    return returnFilter;
  }

  abstract getPage(firstPage?: boolean): void;
}
