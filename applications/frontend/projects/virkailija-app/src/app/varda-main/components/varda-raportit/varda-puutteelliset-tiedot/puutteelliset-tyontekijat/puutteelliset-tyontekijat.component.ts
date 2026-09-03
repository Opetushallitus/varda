import {Component, OnInit} from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaUtilityService } from 'projects/virkailija-app/src/app/core/services/varda-utility.service';
import { HenkiloListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import {AbstractPuutteellisetComponent} from '../abstract-puutteelliset.component';
import { VardaVakajarjestajaService } from '../../../../../core/services/varda-vakajarjestaja.service';
import {KoodistoEnum} from "varda-shared";
import {PageEvent} from "@angular/material/paginator";
import {forkJoin} from "rxjs";

@Component({
    selector: 'app-varda-puutteelliset-tyontekijat',
    templateUrl: './puutteelliset-tyontekijat.component.html',
    styleUrls: ['./puutteelliset-tyontekijat.component.css', '../varda-puutteelliset-tiedot.component.css'],
    standalone: false
})
export class VardaPuutteellisetTyontekijatComponent
  extends AbstractPuutteellisetComponent<HenkiloListDTO, TyontekijaListDTO>
  implements OnInit {
  i18n = VirkailijaTranslations;
  henkilot: Array<HenkiloListDTO>;
  errorCodesKey = 'selectedTyontekijatErrorCodes';

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private raportitService: VardaRaportitService,
    private snackBarService: VardaSnackBarService,
    protected utilityService: VardaUtilityService,
    protected translateService: TranslateService,
    vakajarjestajaService: VardaVakajarjestajaService,
  ) {
    super(utilityService, translateService, vakajarjestajaService);
    this.subscriptions.push(this.henkilostoService.listenHenkilostoListUpdate().subscribe(() => this.getErrors()));
  }

  ngOnInit() {
    this.filteredRowsKey = `filteredTyontekijat_${this.selectedVakajarjestaja.id}`;
    const savedFilteredRows = localStorage.getItem(this.filteredRowsKey);
    if (savedFilteredRows) {
      this.filteredRows = JSON.parse(savedFilteredRows);
    }
    this.filteredRowIds = this.filteredRows.map(row => 'tyontekija_id' in row ? row.tyontekija_id : undefined);
    this.searchFilter.rows_filter = this.filteredRowIds.join(',');

    super.ngOnInit();
  }

  getErrors(): void {
    this.henkilot = null;
    this.isLoading.next(true);

    const tyontekijatErrors$ = this.raportitService.getTyontekijatErrors(this.selectedVakajarjestaja.id);
    const tyontekijaErrorList$ = this.raportitService.getTyontekijaErrorList(this.selectedVakajarjestaja.id, this.getFilter());

    forkJoin([tyontekijatErrors$, tyontekijaErrorList$]).subscribe({
      next: ([tyontekijatErrorsData, tyontekijaErrorListData]) => {
        this.errorCodes = tyontekijatErrorsData.error_codes;
        this.setFilteredErrorCodes();

        this.henkilot = tyontekijaErrorListData.results;
        this.searchFilter.count = tyontekijaErrorListData.count;
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService),
      complete: () => setTimeout(() => this.isLoading.next(false), 500)
    });
  }

  openForm(suhde: TyontekijaListDTO): void {
    this.openHenkiloForm.emit({ ...suhde, rooli: HenkiloRooliEnum.tyontekija });
  }

  errorClicked(henkilo: HenkiloListDTO) {
    this.henkilostoService.getVakajarjestajaTyontekijat(this.selectedVakajarjestaja.id, { search: henkilo.henkilo_oid }).subscribe({
      next: henkiloData => {
        const foundTyontekija = henkiloData.results.find(tyontekija => tyontekija.henkilo_oid === henkilo.henkilo_oid);
        const foundSuhde = foundTyontekija?.tyontekijat.find(suhde => suhde.id === henkilo.tyontekija_id);
        this.openForm({ ...foundSuhde, henkilo_id: foundTyontekija.id, henkilo_oid: foundTyontekija.henkilo_oid });
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService)
    });
  }

  filterClicked(instance: HenkiloListDTO) {
    this.filteredRows.push(instance);
    const index = this.henkilot.findIndex(henkilo => henkilo === instance);
    this.lastRemovedIndices.push(index);
    this.henkilot = this.henkilot.filter(henkilo => henkilo !== instance);
    super.filterClicked(instance);
  }

  removeFilteredRowChip(henkilo: HenkiloListDTO) {
    this.filteredRows = this.filteredRows.filter(row => row !== henkilo);
    const lastIndex = this.lastRemovedIndices.pop();
    this.henkilot.splice(lastIndex, 0, henkilo);
    super.removeFilteredRowChip(henkilo);
  }

  searchErrors(pageEvent?: PageEvent) {
    this.filteredRowIds = this.filteredRows.map(row => 'tyontekija_id' in row ? row.tyontekija_id : undefined);
    super.searchErrors(pageEvent);
  }

  // eslint-disable-next-line @typescript-eslint/member-ordering
  protected readonly KoodistoEnum = KoodistoEnum;
}
