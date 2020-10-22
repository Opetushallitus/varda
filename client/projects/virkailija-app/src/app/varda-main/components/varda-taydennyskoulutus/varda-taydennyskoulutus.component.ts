import { Component, OnInit, ViewChild, OnDestroy } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
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
  styleUrls: ['./varda-taydennyskoulutus.component.css']
})
export class VardaTaydennyskoulutusComponent implements OnInit, OnDestroy {
  @ViewChild(MatSort, { static: true }) tableSort: MatSort;
  i18n = VirkailijaTranslations;
  toimijaAccess: UserAccess;
  toimipaikkaAccessIfAny: UserAccess;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  selectedTaydennyskoulutus: VardaTaydennyskoulutusDTO;
  formValuesChanged: Observable<boolean>;

  displayedColumns = ['nimi', 'osallistuja_lkm', 'suoritus_pvm', 'koulutuspaivia'];
  fullTaydennyskoulutusData: Array<VardaTaydennyskoulutusDTO>;
  taydennyskoulutusData: MatTableDataSource<VardaTaydennyskoulutusDTO>;
  subscriptions: Array<Subscription> = [];

  searchFilter = {
    page_size: 20,
    page: 1,
    count: 0
  };


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

    this.modalService.getModalOpen().pipe(filter(isOpen => !isOpen)).subscribe(isOpen => {
      this.selectedTaydennyskoulutus = null;
    });

    this.subscriptions.push(this.tableSort.sortChange.pipe(filter(Boolean)).subscribe(() => this.searchTaydennyskoulutukset()));
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
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
    const searchParams = { vakajarjestaja_oid: this.vakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid };
    this.henkilostoService.getTaydennyskoulutukset(searchParams).subscribe({
      next: taydennyskoulutukset => {
        this.fullTaydennyskoulutusData = taydennyskoulutukset.map(
          taydennyskoulutus => {
            const osallistujaSet = new Set(taydennyskoulutus.taydennyskoulutus_tyontekijat.map(tyontekijaNimike => tyontekijaNimike.henkilo_oid));
            return { ...taydennyskoulutus, osallistuja_lkm: osallistujaSet.size };
          });

        this.searchTaydennyskoulutukset();
        this.taydennyskoulutusData.sort = this.tableSort;
      },
      error: err => console.error(err)
    });
  }

  searchTaydennyskoulutukset(pageEvent?: PageEvent) {
    if (pageEvent) {
      this.searchFilter.page = pageEvent.pageIndex + 1;
      this.searchFilter.page_size = pageEvent.pageSize;
    } else {
      this.searchFilter.page = 1;
    }

    const maxIndex = this.searchFilter.page * this.searchFilter.page_size;
    const minIndex = maxIndex - this.searchFilter.page_size;

    const sortedData = [...this.fullTaydennyskoulutusData];
    const fieldToSort = this.tableSort.active;
    sortedData.sort((a, b) => a[fieldToSort].localeCompare(b[fieldToSort], 'fi'));

    if (this.tableSort.direction === 'desc') {
      sortedData.reverse();
    }

    this.taydennyskoulutusData = new MatTableDataSource<VardaTaydennyskoulutusDTO>([
      ...sortedData.filter((tyontekija, index) => index >= minIndex && index < maxIndex)
    ]);

  }
}
