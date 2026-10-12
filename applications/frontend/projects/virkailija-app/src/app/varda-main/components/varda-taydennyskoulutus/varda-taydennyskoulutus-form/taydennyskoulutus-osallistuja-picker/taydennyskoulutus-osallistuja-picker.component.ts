import { OnInit, Component, ViewChild, Output, Input, EventEmitter, OnChanges, SimpleChanges, OnDestroy } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import {
  VardaTaydennyskoulutusTyontekijaListDTO,
  VardaTaydennyskoulutusTyontekijaSaveDTO
} from 'projects/virkailija-app/src/app/utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { MatTableDataSource } from '@angular/material/table';
import { SelectionModel } from '@angular/cdk/collections';
import { MatSort } from '@angular/material/sort';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { PageEvent } from '@angular/material/paginator';
import { Subscription } from 'rxjs';


@Component({
    selector: 'app-taydennyskoulutus-osallistuja-picker',
    templateUrl: './taydennyskoulutus-osallistuja-picker.component.html',
    styleUrls: [
        './taydennyskoulutus-osallistuja-picker.component.css',
        '../varda-taydennyskoulutus-form.component.css',
        '../../varda-taydennyskoulutus.component.css'
    ],
    standalone: false
})
export class VardaTaydennyskoulutusOsallistujaPickerComponent implements OnChanges, OnInit, OnDestroy {
  @ViewChild(MatSort, { static: true }) tableSort: MatSort;
  @Input() osallistujat: Array<VardaTaydennyskoulutusTyontekijaSaveDTO>;
  @Output() selectOsallistujat = new EventEmitter<Array<VardaTaydennyskoulutusTyontekijaSaveDTO>>(true);
  i18n = VirkailijaTranslations;
  toimijaAccess: UserAccess;
  toimipaikkaAccess: UserAccess;
  selectedToimipaikka: VardaToimipaikkaMinimalDto;
  selectedVakajarjestaja: VardaVakajarjestajaUi;

  displayedColumns = ['select', 'nimi', 'tehtavanimike'];
  tyontekijatData: MatTableDataSource<VardaTaydennyskoulutusTyontekijaListDTO>;
  tableSelection = new SelectionModel<VardaTaydennyskoulutusTyontekijaListDTO>(true, []);

  searchFilter = {
    page_size: 20,
    page: 1,
    count: 0
  };

  next?: string;
  previous?: string;

  private pageCache = new Map<string, {
    data: Array<VardaTaydennyskoulutusTyontekijaListDTO>;
    count: number;
    next?: string;
    previous?: string;
  }>();

  private subscriptions: Array<Subscription> = [];

  constructor(
    private vakajarjestajaService: VardaVakajarjestajaService,
    private henkilostoService: VardaHenkilostoApiService
  ) {
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
  }

  ngOnInit() {
    this.searchHenkilot();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.osallistujat && this.tyontekijatData) {
      const cacheKey = this.getPageCacheKey(
        this.searchFilter.page_size,
        this.searchFilter.page - 1
      );

      const cachedPage = this.pageCache.get(cacheKey);

      if (cachedPage) {
        this.tyontekijatData.data = this.getVisibleTyontekijat(cachedPage.data);
      }

      this.tableSelection.clear();
    }
  }

  isAllSelected() {
    const numSelected = this.tableSelection.selected.length;
    const numRows = this.tyontekijatData?.data.length;
    return numSelected === numRows;
  }

  masterToggle() {
    if (this.isAllSelected()) {
      this.tableSelection.clear();
    } else {
      this.tyontekijatData.data.forEach(row => this.tableSelection.select(row));
    }
  }

  checkboxLabel(row?: VardaTaydennyskoulutusTyontekijaListDTO): string {
    if (!row) {
      return `${this.isAllSelected() ? 'select' : 'deselect'} all`;
    }
    return `${this.tableSelection.isSelected(row) ? 'deselect' : 'select'} row ${row.nimi}`;
  }

  addOsallistuja(osallistuja: VardaTaydennyskoulutusTyontekijaListDTO, koodi: string) {
    const osallistujat = [
      ...this.osallistujat,
      { henkilo_oid: osallistuja.henkilo_oid, tehtavanimike_koodi: koodi, vakajarjestaja_oid: this.selectedVakajarjestaja.organisaatio_oid }
    ];
    this.selectOsallistujat.emit(osallistujat);
  }

  addSelectedOsallistujat() {
    const osallistujat = [...this.osallistujat];
    this.tableSelection.selected.forEach(osallistuja =>
      osallistujat.push({
        henkilo_oid: osallistuja.henkilo_oid,
        vakajarjestaja_oid: this.selectedVakajarjestaja.organisaatio_oid,
        tehtavanimike_koodi: osallistuja.tehtavanimike_koodit.length === 1 ? osallistuja.tehtavanimike_koodit[0] : null
      })
    );
    this.selectOsallistujat.emit(osallistujat);
    this.tableSelection = new SelectionModel<VardaTaydennyskoulutusTyontekijaListDTO>(true, []);
  }

  searchHenkilot(pageEvent?: PageEvent) {
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
      this.tyontekijatData.data = this.getVisibleTyontekijat(cachedPage.data);
      this.tableSelection.clear();
      return;
    }

    let cursor: string | null = null;

    if (pageEvent) {
      const pageSizeChanged = pageEvent.pageSize !== this.searchFilter.page_size;

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
      vakajarjestaja_oid: this.selectedVakajarjestaja.organisaatio_oid,
      page_size: this.searchFilter.page_size
    };

    if (cursor) {
      params.cursor = cursor;
    }

    this.henkilostoService.getTaydennyskoulutuksetTyontekijat(params).subscribe(response => {
      this.searchFilter.count = response.count;
      this.next = response.next;
      this.previous = response.previous;

      const data = response.results
        .map(tyontekija => ({
          ...tyontekija,
          nimi: `${tyontekija.henkilo_sukunimi}, ${tyontekija.henkilo_etunimet}`
        }))
        .filter(tyontekija => tyontekija.tehtavanimike_koodit?.length);

      this.tyontekijatData =
        new MatTableDataSource<VardaTaydennyskoulutusTyontekijaListDTO>(
          this.getVisibleTyontekijat(data)
        );

      this.pageCache.set(
        this.getPageCacheKey(this.searchFilter.page_size, this.searchFilter.page - 1),
        {
          data,
          count: response.count,
          next: response.next,
          previous: response.previous
        }
      );

      const selectedEntries = this.tableSelection.selected;
      this.tableSelection =
        new SelectionModel<VardaTaydennyskoulutusTyontekijaListDTO>(
          true,
          selectedEntries
        );
    });
  }

  private getVisibleTyontekijat(
    tyontekijat: Array<VardaTaydennyskoulutusTyontekijaListDTO>
  ): Array<VardaTaydennyskoulutusTyontekijaListDTO> {
    return tyontekijat
      .filter(tyontekija => tyontekija.tehtavanimike_koodit?.length)
      .filter(tyontekija =>
        !this.osallistujat.some(
          osallistuja => osallistuja.henkilo_oid === tyontekija.henkilo_oid
        )
      );
  }

  private getPageCacheKey(pageSize: number, pageIndex: number): string {
    return `${pageSize}-${pageIndex}`;
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
