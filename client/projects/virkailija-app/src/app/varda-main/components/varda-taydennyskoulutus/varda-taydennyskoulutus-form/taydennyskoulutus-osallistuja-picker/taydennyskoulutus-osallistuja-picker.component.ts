import { OnInit, Component, ViewChild, Output, Input, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaTaydennyskoulutusTyontekijaDTO, VardaTaydennyskoulutusTyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { MatTableDataSource } from '@angular/material/table';
import { SelectionModel } from '@angular/cdk/collections';
import { MatSort } from '@angular/material/sort';


@Component({
  selector: 'app-taydennyskoulutus-osallistuja-picker',
  templateUrl: './taydennyskoulutus-osallistuja-picker.component.html',
  styleUrls: [
    './taydennyskoulutus-osallistuja-picker.component.css',
    '../varda-taydennyskoulutus-form.component.css',
    '../../varda-taydennyskoulutus.component.css'
  ]
})
export class VardaTaydennyskoulutusOsallistujaPickerComponent implements OnChanges {

  @ViewChild(MatSort, { static: true }) tableSort: MatSort;
  @Input() tyontekijaList: Array<VardaTaydennyskoulutusTyontekijaListDTO>;
  @Input() osallistujat: Array<VardaTaydennyskoulutusTyontekijaDTO>;
  @Output() selectOsallistujat = new EventEmitter<Array<VardaTaydennyskoulutusTyontekijaDTO>>(true);
  i18n = VirkailijaTranslations;
  toimijaAccess: UserAccess;
  toimipaikkaAccess: UserAccess;
  selectedToimipaikka: VardaToimipaikkaMinimalDto;
  searhFilter: string;

  displayedColumns = ['select', 'nimi', 'tehtavanimike'];
  tyontekijatData: MatTableDataSource<VardaTaydennyskoulutusTyontekijaListDTO>;
  tableSelection = new SelectionModel<VardaTaydennyskoulutusTyontekijaListDTO>(true, []);

  constructor(
    private authService: AuthService,
    private henkilostoService: VardaHenkilostoApiService,
    private vakajarjestajaService: VardaVakajarjestajaService
  ) {

  }

  ngOnChanges(change: SimpleChanges) {
/*     console.log(change);

    this.tyontekijatData = new MatTableDataSource<VardaTaydennyskoulutusTyontekijaListDTO>([
      ...this.tyontekijaList.filter(tyontekija => !this.osallistujat.find(osallistuja => osallistuja.henkilo_oid === tyontekija.henkilo_oid))
    ]);
    this.tableSelection = new SelectionModel<VardaTaydennyskoulutusTyontekijaListDTO>(true, []);
    this.tyontekijatData.sort = this.tableSort; */
  }
/*
  isAllSelected() {
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

  addOsallistuja(osallistuja: VardaTaydennyskoulutusTyontekijaListDTO, koodi: string) {
    const osallistujat = [...this.osallistujat, { henkilo_oid: osallistuja.henkilo_oid, tehtavanimike_koodi: koodi }];
    this.selectOsallistujat.emit(osallistujat);
  }

  addSelectedOsallistujat() {
    const osallistujat = [...this.osallistujat];
    this.tableSelection.selected.forEach(osallistuja =>
      osallistujat.push({
        henkilo_oid: osallistuja.henkilo_oid,
        tehtavanimike_koodi: osallistuja.tehtavanimike_koodit.length === 1 ? osallistuja.tehtavanimike_koodit[0] : null
      })
    );
    this.selectOsallistujat.emit(osallistujat);
  } */

}
