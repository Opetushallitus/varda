import {Component, OnInit} from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaUtilityService } from 'projects/virkailija-app/src/app/core/services/varda-utility.service';
import { HenkiloListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';
import { LapsiListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import {AbstractPuutteellisetComponent} from '../abstract-puutteelliset.component';
import { VardaVakajarjestajaService } from '../../../../../core/services/varda-vakajarjestaja.service';
import {KoodistoEnum} from "varda-shared";
import {PageEvent} from "@angular/material/paginator";
import {forkJoin} from "rxjs";

@Component({
    selector: 'app-varda-puutteelliset-lapset',
    templateUrl: './puutteelliset-lapset.component.html',
    styleUrls: ['./puutteelliset-lapset.component.css', '../varda-puutteelliset-tiedot.component.css'],
    standalone: false
})
export class VardaPuutteellisetLapsetComponent
  extends AbstractPuutteellisetComponent<HenkiloListDTO, LapsiListDTO>
  implements OnInit{
  i18n = VirkailijaTranslations;
  henkilot: Array<HenkiloListDTO>;
  errorCodesKey = 'selectedLapsetErrorCodes';

  constructor(
    private lapsiService: VardaLapsiService,
    private raportitService: VardaRaportitService,
    private snackBarService: VardaSnackBarService,
    protected utilityService: VardaUtilityService,
    protected translateService: TranslateService,
    vakajarjestajaService: VardaVakajarjestajaService,
  ) {
    super(utilityService, translateService, vakajarjestajaService);

    this.subscriptions.push(this.lapsiService.listenLapsiListUpdate().subscribe(() => this.getErrors()));
  }

  ngOnInit() {
    this.filteredRowsKey = `filteredLapset_${this.selectedVakajarjestaja.id}`;
    const savedFilteredRows = localStorage.getItem(this.filteredRowsKey);
    if (savedFilteredRows) {
      this.filteredRows = JSON.parse(savedFilteredRows);
    }
    this.filteredRowIds = this.filteredRows.map(row => 'lapsi_id' in row ? row.lapsi_id : undefined);
    this.searchFilter.rows_filter = this.filteredRowIds.join(',');
    super.ngOnInit();
  }

  getErrors(): void {
    this.henkilot = null;
    this.isLoading.next(true);

    const lapsiErrors$ = this.raportitService.getLapsiErrors(this.selectedVakajarjestaja.id);
    const lapsiErrorList$ = this.raportitService.getLapsiErrorList(this.selectedVakajarjestaja.id, this.getFilter());

    forkJoin([lapsiErrors$, lapsiErrorList$]).subscribe({
      next: ([lapsiErrorsData, lapsiErrorListData]) => {
        this.errorCodes = lapsiErrorsData.error_codes;
        this.setFilteredErrorCodes();

        this.henkilot = lapsiErrorListData.results;
        this.searchFilter.count = lapsiErrorListData.count;
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService),
      complete: () => setTimeout(() => this.isLoading.next(false), 500)
    });
  }

  openForm(suhde: LapsiListDTO): void {
    this.openHenkiloForm.emit({ ...suhde, rooli: HenkiloRooliEnum.lapsi });
  }

  errorClicked(henkilo: HenkiloListDTO) {
    this.lapsiService.getVakajarjestajaLapset(this.selectedVakajarjestaja.id, { search: henkilo.henkilo_oid }).subscribe({
      next: henkiloData => {
        const foundLapsi = henkiloData.results.find(lapsi => lapsi.henkilo_oid === henkilo.henkilo_oid);
        const foundSuhde = foundLapsi?.lapset.find(suhde => suhde.id === henkilo.lapsi_id);
        this.openForm({...foundSuhde, henkilo_id: foundLapsi.id, henkilo_oid: foundLapsi.henkilo_oid });
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
    this.filteredRowIds = this.filteredRows.map(row => 'lapsi_id' in row ? row.lapsi_id : undefined);
    super.searchErrors(pageEvent);
  }

  // eslint-disable-next-line @typescript-eslint/member-ordering
  protected readonly KoodistoEnum = KoodistoEnum;
}
