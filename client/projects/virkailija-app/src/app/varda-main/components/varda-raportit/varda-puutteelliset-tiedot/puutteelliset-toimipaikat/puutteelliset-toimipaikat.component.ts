import { Component } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaUtilityService } from 'projects/virkailija-app/src/app/core/services/varda-utility.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { AbstractPuutteellisetComponent } from '../abstract-puutteelliset.component';
import { PuutteellinenToimipaikkaListDTO } from '../../../../../utilities/models/dto/varda-puutteellinen-dto.model';
import { VardaVakajarjestajaApiService } from '../../../../../core/services/varda-vakajarjestaja-api.service';
import { VardaToimipaikkaMinimalDto } from '../../../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaVakajarjestajaService } from '../../../../../core/services/varda-vakajarjestaja.service';

@Component({
  selector: 'app-varda-puutteelliset-toimipaikat',
  templateUrl: './puutteelliset-toimipaikat.component.html',
  styleUrls: ['./puutteelliset-toimipaikat.component.css', '../varda-puutteelliset-tiedot.component.css']
})
export class VardaPuutteellisetToimipaikatComponent extends AbstractPuutteellisetComponent<PuutteellinenToimipaikkaListDTO, VardaToimipaikkaMinimalDto> {
  i18n = VirkailijaTranslations;
  toimipaikat: Array<PuutteellinenToimipaikkaListDTO>;

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

  getErrors(): void {
    this.toimipaikat = null;
    this.isLoading.next(true);

    this.raportitService.getToimipaikkaErrorList(this.selectedVakajarjestaja.id, this.getFilter()).subscribe({
      next: data => {
        this.toimipaikat = data.results;
        this.searchFilter.count = data.count;
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService)
    }).add(() => setTimeout(() => this.isLoading.next(false), 500));
  }

  openForm(instance: VardaToimipaikkaMinimalDto): void {
    this.openToimipaikkaForm.emit(instance);
  }

  findInstance(instance: PuutteellinenToimipaikkaListDTO) {
    this.vakajarjestajaApiService.getToimipaikat(this.selectedVakajarjestaja.id, { id: instance.toimipaikka_id }).subscribe({
      next: data => {
        const result = data.find(toimipaikka => toimipaikka.id === instance.toimipaikka_id);
        this.openForm(result);
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService)
    });
  }
}
