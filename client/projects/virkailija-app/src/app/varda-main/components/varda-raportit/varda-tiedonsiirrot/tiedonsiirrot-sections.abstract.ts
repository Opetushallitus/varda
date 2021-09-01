import { OnDestroy, Component, OnInit, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { ActivatedRoute } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Moment } from 'moment';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Subscription, BehaviorSubject, Observable } from 'rxjs';
import { KoodistoEnum } from 'varda-shared';
import { VardaDateService } from '../../../services/varda-date.service';
import { VardaPageDto } from '../../../../utilities/models/dto/varda-page-dto';
import {
  VardaTiedonsiirtoDTO,
  VardaTiedonsiirtoYhteenvetoDTO
} from '../../../../utilities/models/dto/varda-tiedonsiirto-dto.model';
import handyScroll from 'handy-scroll';


export interface TiedonsiirrotSearchFilter {
  cursor?: string;
  reverse?: boolean;
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
export abstract class AbstractTiedonsiirrotSectionsComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('tiedonsiirtoPaginator') tiedonsiirtoPaginator: MatPaginator;
  @ViewChild('scrollContainer') scrollContainer: ElementRef;
  @ViewChild('tiedonsiirtoTable', { read: ElementRef }) tiedonsiirtoTable: ElementRef;
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
  nextCursor = null;
  prevCursor = null;

  searchFilter: TiedonsiirrotSearchFilter = {
    page_size: 20,
    cursor: null,
    reverse: null,
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
  protected errorService: VardaErrorMessageService;
  private resizeObserver: ResizeObserver;
  abstract columnFields: Array<TiedonsiirrotColumnFields>;

  constructor(
    protected authService: AuthService,
    protected translateService: TranslateService,
    protected route: ActivatedRoute,
    protected vakajarjestajaService: VardaVakajarjestajaService,
    protected raportitService: VardaRaportitService
  ) {
    this.errorService = new VardaErrorMessageService(this.translateService);
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

    this.resizeObserver = new ResizeObserver(entries => {
      this.updateHandyScroller();
    });
  }

  ngAfterViewInit() {
    handyScroll.mount(this.scrollContainer.nativeElement);
    this.resizeObserver.observe(this.tiedonsiirtoTable.nativeElement);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
    handyScroll.destroy(this.scrollContainer.nativeElement);
    this.resizeObserver.unobserve(this.tiedonsiirtoTable.nativeElement);
  }

  changePage(pageEvent: PageEvent) {
    if (pageEvent.pageIndex === 0) {
      // First page
      this.searchFilter.reverse = false;
      this.searchFilter.cursor = null;
    } else if (pageEvent.pageIndex === pageEvent.previousPageIndex + 1) {
      // Next page
      this.searchFilter.cursor = this.nextCursor;
    } else if (pageEvent.pageIndex > pageEvent.previousPageIndex) {
      // More than next page -> last page
      this.searchFilter.reverse = true;
      this.searchFilter.cursor = null;
    } else if (pageEvent.pageIndex < pageEvent.previousPageIndex) {
      // Previous page
      this.searchFilter.cursor = this.prevCursor;
    }

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

  parseCursors(data: VardaPageDto<VardaTiedonsiirtoDTO | VardaTiedonsiirtoYhteenvetoDTO>) {
    const nextCursor = this.extractCursorFromUrl(data.next);
    const prevCursor = this.extractCursorFromUrl(data.previous);

    if (this.searchFilter.reverse) {
      this.nextCursor = prevCursor;
      this.prevCursor = nextCursor;
    } else {
      this.nextCursor = nextCursor;
      this.prevCursor = prevCursor;
    }

    if (this.prevCursor) {
      // If there is a previous page, pretend that we are on page 2 so we can move to
      // previous page (1) or first page (0)
      this.tiedonsiirtoPaginator.pageIndex = 2;
    } else {
      // If there is no previous page, we are on the first page
      this.tiedonsiirtoPaginator.pageIndex = 0;
    }

    this.resultCount = (this.tiedonsiirtoPaginator.pageIndex + 1) * this.searchFilter.page_size;
    if (this.nextCursor) {
      // If there is next page available, pretend that there are two more pages available so we can distinguish
      // between moving to the next page (current index + 1) vs. moving to the last page (current index + 2)
      this.resultCount = this.resultCount + 2 * this.searchFilter.page_size;
    }
  }

  updateHandyScroller() {
    // This function should be called every time table width changes (e.g. new data, show/hide filters...)
    handyScroll.update(this.scrollContainer.nativeElement);
  }

  private extractCursorFromUrl(url: string): string {
    if (!url || typeof url !== 'string') {
      return null;
    }
    const cursorRegex = /cursor=(.*?)(&|$)/;
    return unescape(url.match(cursorRegex)[1]);
  }

  abstract getPage(firstPage?: boolean): void;
}
