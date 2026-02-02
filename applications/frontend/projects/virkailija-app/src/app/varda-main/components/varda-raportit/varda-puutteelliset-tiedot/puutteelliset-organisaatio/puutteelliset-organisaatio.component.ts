import {Component, OnInit} from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaUtilityService } from 'projects/virkailija-app/src/app/core/services/varda-utility.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import {AbstractPuutteellisetComponent} from '../abstract-puutteelliset.component';
import { VardaVakajarjestajaService } from '../../../../../core/services/varda-vakajarjestaja.service';
import {
  PuutteellinenOrganisaatioListDTO
} from '../../../../../utilities/models/dto/varda-puutteellinen-dto.model';
import { Router } from '@angular/router';
import {KoodistoEnum} from "varda-shared";
import {PageEvent} from "@angular/material/paginator";
import {forkJoin} from "rxjs";

@Component({
    selector: 'app-varda-puutteelliset-organisaatio',
    templateUrl: './puutteelliset-organisaatio.component.html',
    styleUrls: ['./puutteelliset-organisaatio.component.css', '../varda-puutteelliset-tiedot.component.css'],
    standalone: false
})
export class VardaPuutteellisetOrganisaatioComponent
  extends AbstractPuutteellisetComponent<PuutteellinenOrganisaatioListDTO, undefined>
  implements OnInit {
  i18n = VirkailijaTranslations;
  organisaatioList: Array<PuutteellinenOrganisaatioListDTO>;
  errorCodesKey = 'selectedOrganisaatioErrorCodes';

  constructor(
    private raportitService: VardaRaportitService,
    private snackBarService: VardaSnackBarService,
    private router: Router,
    protected utilityService: VardaUtilityService,
    protected translateService: TranslateService,
    vakajarjestajaService: VardaVakajarjestajaService,
  ) {
    super(utilityService, translateService, vakajarjestajaService);
  }

  ngOnInit() {
    this.filteredRowsKey = `filteredOrganisaatio_${this.selectedVakajarjestaja.id}`;
    const savedFilteredRows = localStorage.getItem(this.filteredRowsKey);
    if (savedFilteredRows) {
      this.filteredRows = JSON.parse(savedFilteredRows);
    }
    this.filteredRowIds = this.filteredRows.map(row => 'organisaatio_id' in row ? row.organisaatio_id : undefined);
    this.searchFilter.rows_filter = this.filteredRowIds.join(',');
    super.ngOnInit();
  }

  getErrors(): void {
    this.organisaatioList = null;
    this.isLoading.next(true);

    const organisaatioErrors$ = this.raportitService.getOrganisaatioErrors(this.selectedVakajarjestaja.id);
    const organisaatioErrorList$ = this.raportitService.getOrganisaatioErrorList(this.selectedVakajarjestaja.id, this.getFilter());

    forkJoin([organisaatioErrors$, organisaatioErrorList$]).subscribe({
      next: ([organisaatioErrorsData, organisaatioErrorListData]) => {
        this.errorCodes = organisaatioErrorsData.error_codes;
        this.setFilteredErrorCodes();

        this.organisaatioList = organisaatioErrorListData.results;
        this.searchFilter.count = organisaatioErrorListData.count;
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService),
      complete: () => setTimeout(() => this.isLoading.next(false), 500)
    });
  }

  errorClicked(instance: PuutteellinenOrganisaatioListDTO) {
    if (instance.errors.find(error => error.error_code.toUpperCase() === 'VJ010')) {
      // If VJ010 is one of the errors, navigate to /vakatoimija
      this.router.navigate(['/vakatoimija']);
    }
  }


  filterClicked(instance: PuutteellinenOrganisaatioListDTO) {
    this.filteredRows.push(instance);
    const index = this.organisaatioList.findIndex(organisaatio => organisaatio === instance);
    this.lastRemovedIndices.push(index);
    this.organisaatioList = this.organisaatioList.filter(organisaatio => organisaatio !== organisaatio);
    super.filterClicked(instance);
  }

  removeFilteredRowChip(organisaatio: PuutteellinenOrganisaatioListDTO) {
    this.filteredRows = this.filteredRows.filter(row => row !== organisaatio);
    const lastIndex = this.lastRemovedIndices.pop();
    this.organisaatioList.splice(lastIndex, 0, organisaatio);
    super.removeFilteredRowChip(organisaatio);
  }

  searchErrors(pageEvent?: PageEvent) {
    this.filteredRowIds = this.filteredRows.map(row => 'organisaatio_id' in row ? row.organisaatio_id : undefined);
    super.searchErrors(pageEvent);
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  openForm(instance: undefined) {}

  // eslint-disable-next-line @typescript-eslint/member-ordering
  protected readonly KoodistoEnum = KoodistoEnum;
}
