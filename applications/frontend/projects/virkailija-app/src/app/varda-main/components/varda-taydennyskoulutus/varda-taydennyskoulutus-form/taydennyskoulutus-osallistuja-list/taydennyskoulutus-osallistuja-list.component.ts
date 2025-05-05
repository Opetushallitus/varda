import { Component, ViewChild, Input, Output, EventEmitter, SimpleChanges, OnChanges } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { MatSort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import {
  VardaTaydennyskoulutusTyontekijaListDTO,
  VardaTaydennyskoulutusTyontekijaDTO,
  VardaTaydennyskoulutusTyontekijaSaveDTO
} from 'projects/virkailija-app/src/app/utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { SelectionModel } from '@angular/cdk/collections';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';

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
  @Input() isDisabled: boolean;
  @Input() userAccess: UserAccess;
  @Output() selectOsallistujat = new EventEmitter<Array<VardaTaydennyskoulutusTyontekijaSaveDTO>>(true);
  @Output() openTyontekijatList = new EventEmitter<boolean>(true);

  i18n = VirkailijaTranslations;
  selectedToimipaikka: VardaToimipaikkaMinimalDto;
  selectedVakajarjestaja: VardaVakajarjestajaUi;

  columns = ['select', 'nimi', 'tehtavanimike', 'delete'];
  displayedColumns = [...this.columns];
  tyontekijatData: MatTableDataSource<VardaTaydennyskoulutusTyontekijaListDTO>;
  tableSelection = new SelectionModel<VardaTaydennyskoulutusTyontekijaListDTO>(true, []);

  constructor(
    private vakaJarjestajaService: VardaVakajarjestajaService
  ) {
    this.selectedVakajarjestaja = vakaJarjestajaService.getSelectedVakajarjestaja();

  }

  ngOnChanges(change: SimpleChanges) {
    if (change.isDisabled) {
      this.displayedColumns = this.isDisabled ? ['nimi', 'tehtavanimike'] : ['select', 'nimi', 'tehtavanimike', 'delete'];
    }

    this.tyontekijatData = new MatTableDataSource<VardaTaydennyskoulutusTyontekijaListDTO>([
      ...this.tyontekijaList.filter(tyontekija => {
        const tyontekijaValitutNimikkeet = this.osallistujat
          .filter(osallistuja => osallistuja.henkilo_oid === tyontekija.henkilo_oid)
          .map(osallistuja => osallistuja.tehtavanimike_koodi);

        if (tyontekijaValitutNimikkeet?.length) {
          tyontekija.valitut_nimikkeet = tyontekijaValitutNimikkeet;
          return true;
        }
        return false;
      })
    ]);
    this.tableSelection = new SelectionModel<VardaTaydennyskoulutusTyontekijaListDTO>(true, []);
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

  removeOsallistuja(poistettuOsallistuja: VardaTaydennyskoulutusTyontekijaListDTO) {
    const osallistujat = [...this.osallistujat.filter(osallistuja => osallistuja.henkilo_oid !== poistettuOsallistuja.henkilo_oid)];
    this.selectOsallistujat.emit(osallistujat);
  }

  removeSelectedOsallistujat() {
    const henkilo_oids = this.tableSelection.selected.map(osallistuja => osallistuja.henkilo_oid);
    const osallistujat = this.osallistujat.filter(osallistuja => !henkilo_oids.includes(osallistuja.henkilo_oid));
    this.selectOsallistujat.emit(osallistujat);
  }

  changeValitutNimikkeet(tyontekija: VardaTaydennyskoulutusTyontekijaListDTO) {
    const withoutTyontekijaOsallistujat = this.osallistujat.filter(osallistuja => osallistuja.henkilo_oid !== tyontekija.henkilo_oid);
    const tyontekijaOsallistumiset = tyontekija.valitut_nimikkeet.length ?
      tyontekija.valitut_nimikkeet.map(nimikekoodi => ({
          henkilo_oid: tyontekija.henkilo_oid,
          vakajarjestaja_oid: this.selectedVakajarjestaja.organisaatio_oid,
          tehtavanimike_koodi: nimikekoodi
        })) : [{
        henkilo_oid: tyontekija.henkilo_oid,
        vakajarjestaja_oid: this.selectedVakajarjestaja.organisaatio_oid,
        tehtavanimike_koodi: null
      }];

    this.selectOsallistujat.emit([...withoutTyontekijaOsallistujat, ...tyontekijaOsallistumiset]);
  }
}
