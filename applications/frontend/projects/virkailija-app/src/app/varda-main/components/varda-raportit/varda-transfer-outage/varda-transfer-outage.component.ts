import { Component, OnDestroy, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { TranslateService } from '@ngx-translate/core';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';
import { VardaRaportitService } from '../../../../core/services/varda-raportit.service';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';
import { ErrorTree, VardaErrorMessageService } from '../../../../core/services/varda-error-message.service';
import { TransferOutage, TransferOutageSearchFilter } from '../../../../utilities/models/dto/varda-transfer-outage-dto.model';
import { filter } from 'rxjs/operators';
import { NavigationEnd, Router } from '@angular/router';
import { KoodistoDTO, KoodistoEnum, VardaKoodistoService, VardaDateService } from 'varda-shared';
import { Sort } from '@angular/material/sort';
import { DateTime } from 'luxon';
import { extractCursor } from "../../../../utilities/helper-functions";


@Component({
    selector: 'app-varda-transfer-outage',
    templateUrl: './varda-transfer-outage.component.html',
    styleUrls: ['./varda-transfer-outage.component.css'],
    standalone: false
})
export class VardaTransferOutageComponent implements OnInit, OnDestroy {
  resultCount: number = 0;
  nextCursor: string | null = null;
  prevCursor: string | null = null;
  i18n = VirkailijaTranslations;
  isLoading = new BehaviorSubject<boolean>(true);
  errors: Observable<Array<ErrorTree>>;
  displayedColumns = [];
  koodistoEnum = KoodistoEnum;

  subscriptions: Array<Subscription> = [];

  companyTypes = [
    {value: '', viewValue: this.i18n.transfer_outage_all},
    {value: 'municipality', viewValue: this.i18n.transfer_outage_municipality},
    {value: 'private', viewValue: this.i18n.transfer_outage_private},
  ];

  lahdejarjestelmaKoodisto: Observable<KoodistoDTO>;

  displayAll = false;
  activeOrganizations = false;
  selectedCompanyType= '';
  oldTimestampBefore: DateTime;
  oldTimestampAfter: DateTime;
  searchFilter: TransferOutageSearchFilter = {
    page_size: 20,
    timestamp_before: DateTime.now(),
    timestamp_after: DateTime.now().minus({ days: 7 }),
    username: null,
    vakajarjestaja: null,
    lahdejarjestelma: null,
    ordering: 'last_successful_max',
    group_by: 'palvelukayttaja',
    active_organizations: false,
    company_type: '',
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
        () => this.setPage()
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
      page_size: this.searchFilter.page_size,
      group_by: this.searchFilter.group_by,
      ordering: this.searchFilter.ordering,
      active_organizations: this.searchFilter.active_organizations,
      company_type: this.searchFilter.company_type,
    };

    if (this.searchFilter.cursor) {
      parsedFilter.cursor = this.searchFilter.cursor;
    }

    if (this.searchFilter.timestamp_after && this.searchFilter.timestamp_after.isValid) {
      parsedFilter.timestamp_after = this.dateService.luxonToVardaDate(this.searchFilter.timestamp_after);
    }

    if (this.searchFilter.timestamp_before && this.searchFilter.timestamp_before.isValid) {
      parsedFilter.timestamp_before = this.dateService.luxonToVardaDate(this.searchFilter.timestamp_before);
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
        this.displayedColumns = ['username', 'lahdejarjestelma', 'last_successful_max', 'last_unsuccessful_max'];
    }

    this.raportitService.getTransferOutage(parsedFilter).subscribe({
      next: data => {
        this.result = data.results;
        this.resultCount = data.count;
        this.nextCursor = extractCursor(data.next);
        this.prevCursor = extractCursor(data.previous);
      },
      error: (err) => this.errorService.handleError(err)
    }).add(() => setTimeout(() => this.isLoading.next(false), 1000));
  }

  searchTransferOutage(pageEvent?: PageEvent) {
    if (pageEvent) {
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

      const tomorrow = DateTime.now().plus({ days: 1 });

      this.searchFilter.timestamp_after = tomorrow;
      this.searchFilter.timestamp_before = tomorrow;
    } else {
      this.searchFilter.timestamp_after = this.oldTimestampAfter;
      this.searchFilter.timestamp_before = this.oldTimestampBefore;
    }
    this.searchTransferOutage();
  }

  activeOrganizationChange() {
    this.searchFilter.active_organizations = this.activeOrganizations;
    this.searchTransferOutage();
  }

  companyTypeChange() {
    this.searchFilter.company_type = this.selectedCompanyType;
    this.searchTransferOutage();
  }

  setPage() {
    this.searchFilter.group_by = this.router.url.split('?').shift().split('/').pop();
    this.getTransferOutage();
  }
}
