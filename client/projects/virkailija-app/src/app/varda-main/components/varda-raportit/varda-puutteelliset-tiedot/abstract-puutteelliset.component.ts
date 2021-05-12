import { Input, Output, EventEmitter, OnDestroy, Component, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { TranslateService } from '@ngx-translate/core';
import { VardaErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaUtilityService } from 'projects/virkailija-app/src/app/core/services/varda-utility.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { Subscription, BehaviorSubject, Observable } from 'rxjs';

export interface PuutteellinenSearchFilter {
  page: number;
  page_size: number;
  search?: string;
  count?: number;
}

@Component({
  template: ''
})
export abstract class AbstractPuutteellisetComponent<T, Y> implements OnInit, OnDestroy {
  @Input() selectedToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() toimipaikkaAccess: UserAccess;
  @Output() openHenkiloForm = new EventEmitter<Y>(true);
  @Output() openToimipaikkaForm = new EventEmitter<Y>(true);

  protected errorService: VardaErrorMessageService;
  formErrors: Observable<Array<ErrorTree>>;
  subscriptions: Array<Subscription> = [];
  isLoading = new BehaviorSubject<boolean>(false);
  searchFilter: PuutteellinenSearchFilter = {
    page_size: 20,
    page: 1,
    count: 0
  };

  constructor(
    protected utilityService: VardaUtilityService,
    protected translateService: TranslateService,
  ) {
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.formErrors = this.errorService.initErrorList();
  }

  ngOnInit() {
    this.getErrors();
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }

  getFilter(): PuutteellinenSearchFilter {
    const cleanSearchFilter: PuutteellinenSearchFilter = {
      page: null,
      page_size: null,
    };

    Object.entries(this.searchFilter).filter(([key, value]) => value).forEach(([key, value]) => cleanSearchFilter[key] = this.utilityService.hashHetu(value));

    return cleanSearchFilter;
  }

  searchErrors(pageEvent?: PageEvent) {
    if (pageEvent) {
      this.searchFilter.page = pageEvent.pageIndex + 1;
      this.searchFilter.page_size = pageEvent.pageSize;
    } else {
      this.searchFilter.page = 1;
    }

    this.getErrors();
  }

  abstract getErrors(): void;
  abstract findInstance(instance: T): void;
  abstract openForm(instance: Y): void;
}
