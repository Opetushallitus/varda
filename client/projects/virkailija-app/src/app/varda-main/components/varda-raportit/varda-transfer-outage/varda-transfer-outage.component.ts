import { Component, OnDestroy, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { TranslateService } from '@ngx-translate/core';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';
import { VardaRaportitService } from '../../../../core/services/varda-raportit.service';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';
import { ErrorTree, VardaErrorMessageService } from '../../../../core/services/varda-error-message.service';
import { TransferOutage, TransferOutageSearchFilter } from '../../../../utilities/models/dto/varda-transfer-outage-dto.model';
import * as moment from 'moment';
import { filter } from 'rxjs/operators';
import { NavigationEnd, Router } from '@angular/router';
import { KoodistoDTO, KoodistoEnum, VardaKoodistoService, VardaDateService } from 'varda-shared';
import { Sort } from '@angular/material/sort';
import { Moment } from 'moment';


@Component({
  selector: 'app-varda-transfer-outage',
  templateUrl: './varda-transfer-outage.component.html',
  styleUrls: ['./varda-transfer-outage.component.css']
})
export class VardaTransferOutageComponent implements OnInit, OnDestroy {
  i18n = VirkailijaTranslations;
  isLoading = new BehaviorSubject<boolean>(true);
  errors: Observable<Array<ErrorTree>>;
  displayedColumns = [];
  koodistoEnum = KoodistoEnum;

  subscriptions: Array<Subscription> = [];

  lahdejarjestelmaKoodisto: Observable<KoodistoDTO>;

  displayAll = false;
  oldTimestampBefore: Moment;
  oldTimestampAfter: Moment;
  searchFilter: TransferOutageSearchFilter = {
    count: 0,
    page: 1,
    page_size: 20,
    timestamp_before: moment(),
    timestamp_after: moment().subtract(7, 'days'),
    username: null,
    vakajarjestaja: null,
    lahdejarjestelma: null,
    ordering: 'last_successful_max',
    group_by: 'palvelukayttaja',
  };
  result: Array<TransferOutage>;

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
    this.oldTimestampAfter = this.searchFilter.timestamp_after;
    this.oldTimestampBefore = this.searchFilter.timestamp_before;
  }

  ngOnInit() {
    this.subscriptions.push(
      this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe(
        (navigation: NavigationEnd) => this.setPage()
      ),
    );
    this.lahdejarjestelmaKoodisto = this.koodistoService.getKoodisto(KoodistoEnum.lahdejarjestelma);
    this.setPage();
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  getTransferOutage() {
    this.isLoading.next(true);
    this.result = null;

    const parsedFilter: Record<string, unknown> = {
      page: this.searchFilter.page,
      page_size: this.searchFilter.page_size,
      group_by: this.searchFilter.group_by,
      ordering: this.searchFilter.ordering
    };

    if (this.searchFilter.timestamp_after && this.searchFilter.timestamp_after.isValid()) {
      parsedFilter.timestamp_after = this.dateService.momentToVardaDate(this.searchFilter.timestamp_after);
    }

    if (this.searchFilter.timestamp_before && this.searchFilter.timestamp_before.isValid()) {
      parsedFilter.timestamp_before = this.dateService.momentToVardaDate(this.searchFilter.timestamp_before);
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

    switch (this.searchFilter.group_by) {
      case 'organisaatio':
        this.displayedColumns = ['vakajarjestajaOid', 'vakajarjestajaName', 'last_successful_max', 'last_unsuccessful_max'];
        break;
      case 'lahdejarjestelma':
        this.displayedColumns = ['lahdejarjestelma', 'last_successful_max', 'last_unsuccessful_max'];
        break;
      case 'palvelukayttaja':
      default:
        this.displayedColumns = ['username', 'last_successful_max', 'last_unsuccessful_max'];
    }

    this.raportitService.getTransferOutage(parsedFilter).subscribe({
      next: data => {
        this.result = data.results;
        this.searchFilter.count = data.count;
      },
      error: (err) => this.errorService.handleError(err)
    }).add(() => setTimeout(() => this.isLoading.next(false), 1000));
  }

  searchTransferOutage(pageEvent?: PageEvent) {
    if (pageEvent) {
      this.searchFilter.page = pageEvent.pageIndex + 1;
      this.searchFilter.page_size = pageEvent.pageSize;
    } else {
      this.searchFilter.page = 1;
    }

    this.getTransferOutage();
  }

  sortChange(sort: Sort) {
    if (!sort.direction) {
      this.searchFilter.ordering = 'last_successful_max';
    } else {
      this.searchFilter.ordering = `${sort.direction === 'desc' ? '-' : ''}${sort.active}`;
    }
    this.searchTransferOutage();
  }

  displayAllChange() {
    if (this.displayAll) {
      this.oldTimestampAfter = this.searchFilter.timestamp_after;
      this.oldTimestampBefore = this.searchFilter.timestamp_before;
      const tomorrow = moment().add(1, 'days');
      this.searchFilter.timestamp_after = tomorrow;
      this.searchFilter.timestamp_before = tomorrow;
    } else {
      this.searchFilter.timestamp_after = this.oldTimestampAfter;
      this.searchFilter.timestamp_before = this.oldTimestampBefore;
    }
    this.searchTransferOutage();
  }

  setPage() {
    this.searchFilter.group_by = this.router.url.split('?').shift().split('/').pop();
    this.getTransferOutage();
  }
}
