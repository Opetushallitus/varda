import { Component, OnInit, ViewChild } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { AuthService } from '../../../core/auth/auth.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { VardaTaydennyskoulutusDTO } from '../../../utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { VardaHenkilostoApiService } from '../../../core/services/varda-henkilosto.service';
import { MatTableDataSource } from '@angular/material/table';
import { SelectionModel } from '@angular/cdk/collections';
import { MatSort } from '@angular/material/sort';
import { ModalEvent } from '../../../shared/components/varda-modal-form/varda-modal-form.component';

@Component({
  selector: 'app-varda-taydennyskoulutus',
  templateUrl: './varda-taydennyskoulutus.component.html',
  styleUrls: ['./varda-taydennyskoulutus.component.css']
})
export class VardaTaydennyskoulutusComponent implements OnInit {
  @ViewChild(MatSort, { static: true }) tableSort: MatSort;
  i18n = VirkailijaTranslations;
  toimijaAccess: UserAccess;
  toimipaikkaAccessIfAny: UserAccess;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  selectedTaydennyskoulutus: VardaTaydennyskoulutusDTO;

  displayedColumns = ['nimi', 'osallistuja_lkm', 'suoritus_pvm', 'koulutuspaivia'];
  taydennyskoulutusData: MatTableDataSource<VardaTaydennyskoulutusDTO>;

  constructor(
    private authService: AuthService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private henkilostoService: VardaHenkilostoApiService,
  ) {
    this.toimijaAccess = this.authService.getUserAccess();
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
  }

  ngOnInit() {
    /* this.getTaydennyskoulutukset(); */
  }


 /*  openTaydennyskoulutus(taydennyskoulutus?: any) {
    this.selectedTaydennyskoulutus = taydennyskoulutus || {};
  }

  closeTaydennyskoulutus(event: ModalEvent) {
    if (event === ModalEvent.hides) {
      this.selectedTaydennyskoulutus = null;
    }
  }

  getTaydennyskoulutukset() {
    const searchParams = { vakajarjestaja_oid: this.vakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid };
    this.henkilostoService.getTaydennyskoulutukset(searchParams).subscribe({
      next: taydennyskoulutukset => {
        this.taydennyskoulutusData = new MatTableDataSource<VardaTaydennyskoulutusDTO>(taydennyskoulutukset.map(
          taydennyskoulutus => {
            return { ...taydennyskoulutus, osallistuja_lkm: taydennyskoulutus.taydennyskoulutus_tyontekijat.length + Math.ceil(Math.random() * 10) };
          }));
        this.taydennyskoulutusData.sort = this.tableSort;
      },
      error: err => console.error(err)
    });
  } */
}
