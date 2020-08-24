import { OnInit, Component, ViewChild, Input, Output, EventEmitter, SimpleChanges, OnChanges } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { MatSort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { VardaTaydennyskoulutusTyontekijaListDTO, VardaTaydennyskoulutusTyontekijaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { SelectionModel } from '@angular/cdk/collections';

@Component({
  selector: 'app-taydennyskoulutus-osallistuja-list',
  templateUrl: './taydennyskoulutus-osallistuja-list.component.html',
  styleUrls: [
    './taydennyskoulutus-osallistuja-list.component.css',
    '../varda-taydennyskoulutus-form.component.css',
    '../../varda-taydennyskoulutus.component.css'
  ]
})
export class VardaTaydennyskoulutusOsallistujaListComponent implements OnChanges {
  @ViewChild(MatSort, { static: true }) tableSort: MatSort;
  @Input() tyontekijaList: Array<VardaTaydennyskoulutusTyontekijaListDTO>;
  @Input() osallistujat: Array<VardaTaydennyskoulutusTyontekijaDTO>;
  @Output() selectOsallistujat = new EventEmitter<Array<VardaTaydennyskoulutusTyontekijaDTO>>(true);
  i18n = VirkailijaTranslations;
  toimijaAccess: UserAccess;
  toimipaikkaAccess: UserAccess;
  selectedToimipaikka: VardaToimipaikkaMinimalDto;


  displayedColumns = ['select', 'nimi', 'tehtavanimike', 'delete'];
  tyontekijatData: MatTableDataSource<VardaTaydennyskoulutusTyontekijaListDTO>;
  tableSelection = new SelectionModel<VardaTaydennyskoulutusTyontekijaListDTO>(true, []);

  constructor(
    private authService: AuthService
  ) {

  }

  ngOnChanges(change: SimpleChanges) {
   /*  console.log(change);

    this.tyontekijatData = new MatTableDataSource<VardaTaydennyskoulutusTyontekijaListDTO>([
      ...this.tyontekijaList.filter(tyontekija => this.osallistujat.find(osallistuja => osallistuja.henkilo_oid === tyontekija.henkilo_oid))
    ]);
    this.tableSelection = new SelectionModel<VardaTaydennyskoulutusTyontekijaListDTO>(true, []);
    this.tyontekijatData.sort = this.tableSort; */
  }

/*   isAllSelected() {
    const numSelected = this.tableSelection.selected.length;
    const numRows = this.tyontekijatData?.data.length;
    return numSelected === numRows;
  }

  masterToggle() {
    this.isAllSelected() ?
      this.tableSelection.clear() :
      this.tyontekijatData.data.forEach(row => this.tableSelection.select(row));
  }

  checkboxLabel(row?: VardaTaydennyskoulutusTyontekijaListDTO): string {
    if (!row) {
      return `${this.isAllSelected() ? 'select' : 'deselect'} all`;
    }
    return `${this.tableSelection.isSelected(row) ? 'deselect' : 'select'} row ${row.nimi}`;
  }


  removeOsallistuja(poistettuOsallistuja: VardaTaydennyskoulutusTyontekijaListDTO) {
    const osallistujat = [...this.osallistujat.filter(osallistuja => osallistuja.henkilo_oid !== poistettuOsallistuja.henkilo_oid)];
    this.selectOsallistujat.emit(osallistujat);
  }

  removeSelectedOsallistujat() {
    const henkilo_oids = this.tableSelection.selected.map(osallistuja => osallistuja.henkilo_oid);
    const osallistujat = this.osallistujat.filter(osallistuja => !henkilo_oids.includes(osallistuja.henkilo_oid));
    this.selectOsallistujat.emit(osallistujat);
  } */

}
