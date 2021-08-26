import { Component, OnDestroy, OnInit } from '@angular/core';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';
import { ErrorTree, VardaErrorMessageService } from '../../../../core/services/varda-error-message.service';
import { KoodistoDTO, KoodistoEnum, VardaKoodistoService } from 'varda-shared';
import * as moment from 'moment';
import { Router } from '@angular/router';
import { VardaRaportitService } from '../../../../core/services/varda-raportit.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaDateService } from '../../../services/varda-date.service';
import { PageEvent } from '@angular/material/paginator';
import {
  RequestSummary,
  RequestSummarySearchFilter
} from '../../../../utilities/models/dto/varda-request-summary-dto.model';

@Component({
  selector: 'app-varda-request-summary',
  templateUrl: './varda-request-summary.component.html',
  styleUrls: ['./varda-request-summary.component.css']
})
export class VardaRequestSummaryComponent implements OnInit, OnDestroy {
  i18n = VirkailijaTranslations;
  isLoading = new BehaviorSubject<boolean>(true);
  errors: Observable<Array<ErrorTree>>;
  displayedColumnsAll = ['target', 'ratio', 'successfulCount', 'unsuccessfulCount', 'summaryDate'];
  displayedColumnsNoDate = ['target', 'ratio', 'successfulCount', 'unsuccessfulCount'];
  displayedColumns = this.displayedColumnsAll;
  displayedHiddenColumns = ['requestMethod', 'requestUrl', 'requestResponseCode', 'requestCount'];
  koodistoEnum = KoodistoEnum;

  subscriptions: Array<Subscription> = [];
  activeLink = 'user';

  lahdejarjestelmaKoodisto: Observable<KoodistoDTO>;

  searchFilter: RequestSummarySearchFilter = {
    count: 0,
    page: 1,
    page_size: 20,
    summary_date_after: moment().subtract(1, 'days'),
    summary_date_before: moment().subtract(1, 'days'),
    username: null,
    vakajarjestaja: null,
    lahdejarjestelma: null,
    request_url_simple: null,
    categories: {
      user: true,
      vakajarjestaja: true,
      lahdejarjestelma: true,
      url: true
    },
    search: null,
    group: 'false'
  };
  result: Array<RequestSummary>;
  expandedInstance: RequestSummary = null;

  private errorService: VardaErrorMessageService;

  constructor(
    private router: Router,
    private raportitService: VardaRaportitService,
    private translateService: TranslateService,
    private dateService: VardaDateService,
    private koodistoService: VardaKoodistoService
  ) {
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.errors = this.errorService.initErrorList();
  }

  ngOnInit(): void {
    this.lahdejarjestelmaKoodisto = this.koodistoService.getKoodisto(KoodistoEnum.lahdejarjestelma);
    this.getRequestSummary();
  }

  getRequestSummary() {
    this.isLoading.next(true);
    this.result = null;
    this.expandedInstance = null;

    const parsedFilter: Record<string, unknown> = {
      page: this.searchFilter.page,
      page_size: this.searchFilter.page_size
    };

    if (this.searchFilter.summary_date_after && this.searchFilter.summary_date_after.isValid()) {
      parsedFilter.summary_date_after = this.dateService.momentToVardaDate(this.searchFilter.summary_date_after);
    }

    if (this.searchFilter.summary_date_before && this.searchFilter.summary_date_before.isValid()) {
      parsedFilter.summary_date_before = this.dateService.momentToVardaDate(this.searchFilter.summary_date_before);
    }

    if (this.searchFilter.username) {
      parsedFilter.username = this.searchFilter.username;
    }

    if (this.searchFilter.lahdejarjestelma) {
      parsedFilter.lahdejarjestelma = this.searchFilter.lahdejarjestelma;
    }

    if (this.searchFilter.vakajarjestaja) {
      parsedFilter.vakajarjestaja = this.searchFilter.vakajarjestaja;
    }

    if (this.searchFilter.request_url_simple) {
      parsedFilter.request_url_simple = this.searchFilter.request_url_simple;
    }

    parsedFilter.group = this.searchFilter.group;

    const categoryList = [];
    for (const [categoryKey, categoryValue] of Object.entries(this.searchFilter.categories)) {
      if (categoryValue) {
        categoryList.push(categoryKey);
      }
    }
    parsedFilter.categories = categoryList.join(',');

    if (this.searchFilter.search) {
      parsedFilter.search = this.searchFilter.search;
    }

    this.raportitService.getRequestSummary(parsedFilter).subscribe({
      next: data => {
        this.result = data.results;
        this.searchFilter.count = data.count;
        this.displayedColumns = this.searchFilter.group === 'false' ? this.displayedColumnsAll : this.displayedColumnsNoDate;
      },
      error: (err) => this.errorService.handleError(err)
    }).add(() => setTimeout(() => this.isLoading.next(false), 1000));
  }

  searchRequestSummary(pageEvent?: PageEvent) {
    if (pageEvent) {
      this.searchFilter.page = pageEvent.pageIndex + 1;
      this.searchFilter.page_size = pageEvent.pageSize;
    } else {
      this.searchFilter.page = 1;
    }

    this.getRequestSummary();
  }

  ngOnDestroy(): void {
  }
}
