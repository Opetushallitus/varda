import {Component, OnInit} from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaUtilityService } from 'projects/virkailija-app/src/app/core/services/varda-utility.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import {AbstractPuutteellisetComponent} from '../abstract-puutteelliset.component';
import {
  PuutteellinenToimipaikkaListDTO
} from '../../../../../utilities/models/dto/varda-puutteellinen-dto.model';
import { VardaVakajarjestajaApiService } from '../../../../../core/services/varda-vakajarjestaja-api.service';
import { VardaToimipaikkaMinimalDto } from '../../../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaVakajarjestajaService } from '../../../../../core/services/varda-vakajarjestaja.service';
import {KoodistoEnum} from "varda-shared";
import {PageEvent} from "@angular/material/paginator";
import {forkJoin} from "rxjs";

@Component({
    selector: 'app-varda-puutteelliset-toimipaikat',
    templateUrl: './puutteelliset-toimipaikat.component.html',
    styleUrls: ['./puutteelliset-toimipaikat.component.css', '../varda-puutteelliset-tiedot.component.css'],
    standalone: false
})
export class VardaPuutteellisetToimipaikatComponent
  extends AbstractPuutteellisetComponent<PuutteellinenToimipaikkaListDTO, VardaToimipaikkaMinimalDto>
  implements OnInit {
  i18n = VirkailijaTranslations;
  toimipaikat: Array<PuutteellinenToimipaikkaListDTO>;
  errorCodesKey = 'selectedToimipaikkaErrorCodes';

  constructor(
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private raportitService: VardaRaportitService,
    private snackBarService: VardaSnackBarService,
    protected utilityService: VardaUtilityService,
    protected translateService: TranslateService,
    vakajarjestajaService: VardaVakajarjestajaService,
  ) {
    super(utilityService, translateService, vakajarjestajaService);
    this.subscriptions.push(this.vakajarjestajaApiService.listenToimipaikkaListUpdate().subscribe(() => this.getErrors()));
  }

    ngOnInit() {
    this.filteredRowsKey = `filteredToimipaikat_${this.selectedVakajarjestaja.id}`;
    const savedFilteredRows = localStorage.getItem(this.filteredRowsKey);
    if (savedFilteredRows) {
      this.filteredRows = JSON.parse(savedFilteredRows);
    }
    this.filteredRowIds = this.filteredRows.map(row => 'toimipaikka_id' in row ? row.toimipaikka_id : undefined);
    this.searchFilter.rows_filter = this.filteredRowIds.join(',');

    super.ngOnInit();
  }

  getErrors(): void {
    this.toimipaikat = null;
    this.isLoading.next(true);

    const toimipaikkaErrors$ = this.raportitService.getToimipaikkaErrors(this.selectedVakajarjestaja.id);
    const toimipaikkaErrorList$ = this.raportitService.getToimipaikkaErrorList(this.selectedVakajarjestaja.id, this.getFilter());

    forkJoin([toimipaikkaErrors$, toimipaikkaErrorList$]).subscribe({
      next: ([toimipaikkaErrorsData, toimipaikkaErrorListData]) => {
        this.errorCodes = toimipaikkaErrorsData.error_codes;
        this.setFilteredErrorCodes();

        this.toimipaikat = toimipaikkaErrorListData.results;
        this.searchFilter.count = toimipaikkaErrorListData.count;
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService),
      complete: () => setTimeout(() => this.isLoading.next(false), 500)
    });
  }

  openForm(instance: VardaToimipaikkaMinimalDto): void {
    this.openToimipaikkaForm.emit(instance);
  }

  errorClicked(instance: PuutteellinenToimipaikkaListDTO) {
    this.vakajarjestajaApiService.getToimipaikat(this.selectedVakajarjestaja.id, { id: instance.toimipaikka_id }).subscribe({
      next: data => {
        const result = data.find(toimipaikka => toimipaikka.id === instance.toimipaikka_id);
        this.openForm(result);
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService)
    });
  }

  filterClicked(instance: PuutteellinenToimipaikkaListDTO) {
    this.filteredRows.push(instance);
    const index = this.toimipaikat.findIndex(toimipaikka => toimipaikka === instance);
    this.lastRemovedIndices.push(index);
    this.toimipaikat = this.toimipaikat.filter(toimipaikka => toimipaikka !== instance);
    super.filterClicked(instance);
  }

  removeFilteredRowChip(toimipaikka: PuutteellinenToimipaikkaListDTO) {
    this.filteredRows = this.filteredRows.filter(row => row !== toimipaikka);
    const lastIndex = this.lastRemovedIndices.pop();
    this.toimipaikat.splice(lastIndex, 0, toimipaikka);
    super.removeFilteredRowChip(toimipaikka)
  }

  searchErrors(pageEvent?: PageEvent) {
    this.filteredRowIds = this.filteredRows.map(row => 'toimipaikka_id' in row ? row.toimipaikka_id : undefined);
    super.searchErrors(pageEvent);
  }

  // eslint-disable-next-line @typescript-eslint/member-ordering
  protected readonly KoodistoEnum = KoodistoEnum;
}
