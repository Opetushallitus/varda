import { Component, OnInit, ViewChild, OnDestroy } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../core/auth/auth.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { VardaTaydennyskoulutusDTO } from '../../../utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { VardaHenkilostoApiService } from '../../../core/services/varda-henkilosto.service';
import { MatTableDataSource } from '@angular/material/table';
import { MatSort } from '@angular/material/sort';
import { ModalEvent } from '../../../shared/components/varda-modal-form/varda-modal-form.component';
import { Observable, Subscription } from 'rxjs';
import { VardaModalService } from '../../../core/services/varda-modal.service';
import { distinctUntilChanged, filter } from 'rxjs/operators';
import { PageEvent } from '@angular/material/paginator';

@Component({
    selector: 'app-varda-taydennyskoulutus',
    templateUrl: './varda-taydennyskoulutus.component.html',
    styleUrls: ['./varda-taydennyskoulutus.component.css'],
    standalone: false
})
export class VardaTaydennyskoulutusComponent implements OnInit, OnDestroy {
  @ViewChild(MatSort, { static: true }) tableSort: MatSort;

  i18n = VirkailijaTranslations;
  toimijaAccess: UserAccess;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  selectedTaydennyskoulutus: VardaTaydennyskoulutusDTO;
  formValuesChanged: Observable<boolean>;

  displayedColumns = ['nimi', 'taydennyskoulutus_tyontekijat_count', 'suoritus_pvm', 'koulutuspaivia'];
  fullTaydennyskoulutusData: Array<VardaTaydennyskoulutusDTO>;
  taydennyskoulutusData: MatTableDataSource<VardaTaydennyskoulutusDTO>;
  subscriptions: Array<Subscription> = [];

  searchFilter = {
    page_size: 20,
    page: 1,
    count: 0
  };

  next?: string;
  previous?: string;

  private pageCache = new Map<string, {
    data: Array<VardaTaydennyskoulutusDTO>;
    count: number;
    next?: string;
    previous?: string;
  }>();

  constructor(
    private authService: AuthService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private henkilostoService: VardaHenkilostoApiService,
    private modalService: VardaModalService
  ) {
    this.toimijaAccess = this.authService.getUserAccess();
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();

    this.formValuesChanged = this.modalService.getFormValuesChanged().pipe(distinctUntilChanged());
  }

  ngOnInit() {
    this.getTaydennyskoulutukset();

    this.subscriptions.push(
      this.modalService.getModalOpen()
        .pipe(filter(isOpen => !isOpen))
        .subscribe(() => {
          this.selectedTaydennyskoulutus = null;
        })
    );
  }


  openTaydennyskoulutus(taydennyskoulutus?: any) {
    this.selectedTaydennyskoulutus = taydennyskoulutus || {};
  }

  closeTaydennyskoulutus(event: ModalEvent) {
    if (event === ModalEvent.hidden) {
      this.selectedTaydennyskoulutus = null;
      this.modalService.setFormValuesChanged(false);
    }
  }

  getTaydennyskoulutukset() {
    this.pageCache.clear();
    this.searchFilter.page = 1;
    this.next = undefined;
    this.previous = undefined;
    this.searchTaydennyskoulutukset();
  }

  searchTaydennyskoulutukset(pageEvent?: PageEvent) {
    const pageSize = pageEvent?.pageSize ?? this.searchFilter.page_size;
    const pageIndex = pageEvent?.pageIndex ?? this.searchFilter.page - 1;
    const cacheKey = this.getPageCacheKey(pageSize, pageIndex);
    const cachedPage = this.pageCache.get(cacheKey);

    if (cachedPage) {
      this.searchFilter.page_size = pageSize;
      this.searchFilter.page = pageIndex + 1;
      this.searchFilter.count = cachedPage.count;
      this.next = cachedPage.next;
      this.previous = cachedPage.previous;

      this.taydennyskoulutusData =
        new MatTableDataSource<VardaTaydennyskoulutusDTO>(cachedPage.data);

      return;
    }

    let cursor: string | null = null;

    if (pageEvent) {
      const pageSizeChanged =
        pageEvent.pageSize !== this.searchFilter.page_size;

      if (pageSizeChanged) {
        this.searchFilter.page_size = pageEvent.pageSize;
        this.searchFilter.page = 1;
        this.next = undefined;
        this.previous = undefined;
      } else {
        const url = pageEvent.pageIndex > this.searchFilter.page - 1
          ? this.next
          : this.previous;

        if (!url) {
          return;
        }

        cursor = new URL(url, window.location.origin).searchParams.get('cursor');
        this.searchFilter.page = pageEvent.pageIndex + 1;
      }
    }

    const params: Record<string, unknown> = {
      vakajarjestaja_oid:
        this.selectedVakajarjestaja.organisaatio_oid,
      page_size: this.searchFilter.page_size
    };

    if (cursor) {
      params.cursor = cursor;
    }

    this.henkilostoService.getTaydennyskoulutukset(params).subscribe({
      next: response => {
        this.searchFilter.count = response.count;
        this.next = response.next;
        this.previous = response.previous;

        this.taydennyskoulutusData =
          new MatTableDataSource<VardaTaydennyskoulutusDTO>(
            response.results
          );

        this.pageCache.set(
          this.getPageCacheKey(
            this.searchFilter.page_size,
            this.searchFilter.page - 1
          ),
          {
            data: response.results,
            count: response.count,
            next: response.next,
            previous: response.previous
          }
        );
      },
      error: err => console.error(err)
    });
  }

  private getPageCacheKey(pageSize: number, pageIndex: number): string {
    return `${pageSize}-${pageIndex}`;
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
