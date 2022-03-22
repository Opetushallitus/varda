import { OnInit, Component, ViewChild, Output, Input, EventEmitter, OnChanges, SimpleChanges, OnDestroy } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import {
  VardaTaydennyskoulutusTyontekijaListDTO,
  VardaTaydennyskoulutusTyontekijaSaveDTO
} from 'projects/virkailija-app/src/app/utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { MatTableDataSource } from '@angular/material/table';
import { SelectionModel } from '@angular/cdk/collections';
import { MatSort } from '@angular/material/sort';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { PageEvent } from '@angular/material/paginator';
import { filter } from 'rxjs/operators';
import { Subscription } from 'rxjs';


@Component({
  selector: 'app-taydennyskoulutus-osallistuja-picker',
  templateUrl: './taydennyskoulutus-osallistuja-picker.component.html',
  styleUrls: [
    './taydennyskoulutus-osallistuja-picker.component.css',
    '../varda-taydennyskoulutus-form.component.css',
    '../../varda-taydennyskoulutus.component.css'
  ]
})
export class VardaTaydennyskoulutusOsallistujaPickerComponent implements OnChanges, OnInit, OnDestroy {
  @ViewChild(MatSort, { static: true }) tableSort: MatSort;
  @Input() tyontekijaList: Array<VardaTaydennyskoulutusTyontekijaListDTO>;
  @Input() osallistujat: Array<VardaTaydennyskoulutusTyontekijaSaveDTO>;
  @Output() selectOsallistujat = new EventEmitter<Array<VardaTaydennyskoulutusTyontekijaSaveDTO>>(true);
  i18n = VirkailijaTranslations;
  toimijaAccess: UserAccess;
  toimipaikkaAccess: UserAccess;
  selectedToimipaikka: VardaToimipaikkaMinimalDto;
  selectedVakajarjestaja: VardaVakajarjestajaUi;

  displayedColumns = ['select', 'nimi', 'tehtavanimike'];
  filteredTyontekijatData: Array<VardaTaydennyskoulutusTyontekijaListDTO>;
  tyontekijatData: MatTableDataSource<VardaTaydennyskoulutusTyontekijaListDTO>;
  tableSelection = new SelectionModel<VardaTaydennyskoulutusTyontekijaListDTO>(true, []);

  searchFilter = {
    page_size: 5,
    page: 1,
    count: 0
  };

  private subscriptions: Array<Subscription> = [];

  constructor(
    private vakajarjestajaService: VardaVakajarjestajaService
  ) {
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
  }

  ngOnInit() {
    this.subscriptions.push(this.tableSort.sortChange.pipe(filter(Boolean)).subscribe(() => this.searchHenkilot()));
  }

  ngOnChanges(change: SimpleChanges) {
    this.filteredTyontekijatData = this.tyontekijaList
      .filter(tyontekija => tyontekija.tehtavanimike_koodit?.length)
      .filter(tyontekija => !this.osallistujat.find(osallistuja => osallistuja.henkilo_oid === tyontekija.henkilo_oid));
    this.filteredTyontekijatData.sort((a, b) => a.nimi.localeCompare(b.nimi, 'fi'));

    this.searchHenkilot();
    this.tyontekijatData.sort = this.tableSort;
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
    const osallistujat = [...this.osallistujat, { henkilo_oid: osallistuja.henkilo_oid, tehtavanimike_koodi: koodi, vakajarjestaja_oid: this.selectedVakajarjestaja.organisaatio_oid }];
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
  }

  searchHenkilot(pageEvent?: PageEvent) {
    if (pageEvent) {
      this.searchFilter.page = pageEvent.pageIndex + 1;
      this.searchFilter.page_size = pageEvent.pageSize;
    } else {
      this.searchFilter.page = 1;
    }

    const maxIndex = this.searchFilter.page * this.searchFilter.page_size;
    const minIndex = maxIndex - this.searchFilter.page_size;

    const sortedData = [...this.filteredTyontekijatData];
    const fieldToSort = this.tableSort.active;
    sortedData.sort((a, b) => a[fieldToSort].localeCompare(b[fieldToSort], 'fi'));

    if (this.tableSort.direction === 'desc') {
      sortedData.reverse();
    }

    this.tyontekijatData = new MatTableDataSource<VardaTaydennyskoulutusTyontekijaListDTO>([
      ...sortedData.filter((tyontekija, index) => index >= minIndex && index < maxIndex)
    ]);
    this.tableSelection = new SelectionModel<VardaTaydennyskoulutusTyontekijaListDTO>(true, []);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
