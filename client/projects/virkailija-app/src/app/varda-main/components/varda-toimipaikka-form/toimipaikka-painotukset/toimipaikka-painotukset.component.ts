import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaUtilityService } from 'projects/virkailija-app/src/app/core/services/varda-utility.service';
import { VardaVakajarjestajaApiService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja-api.service';
import { VardaToimipaikkaDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { KielipainotusDTO, ToiminnallinenPainotusDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Observable } from 'rxjs';
import { CodeDTO, KoodistoDTO, KoodistoEnum, KoodistoSortBy, VardaKoodistoService } from 'varda-shared';

@Component({
  selector: 'app-toimipaikka-painotukset',
  templateUrl: './toimipaikka-painotukset.component.html',
  styleUrls: ['./toimipaikka-painotukset.component.css', '../varda-toimipaikka-form.component.css']
})
export class ToimipaikkaPainotuksetComponent implements OnChanges {
  @Input() toimipaikka: VardaToimipaikkaDTO;
  @Input() kielikoodisto: Array<CodeDTO>;
  @Input() saveAccess: boolean;
  @Input() isEdit: boolean;
  @Input() errorService: VardaErrorMessageService;
  @Input() minStartDate: Date;
  @Input() maxEndDate: Date;
  @Output() toggleKielipainotukset = new EventEmitter<boolean>(true);
  @Output() toggleToimintapainotukset = new EventEmitter<boolean>(true);
  i18n = VirkailijaTranslations;
  kielipainotukset: Array<KielipainotusDTO> = [];
  toimintapainotukset: Array<ToiminnallinenPainotusDTO> = [];
  toimintapainotuksetKoodisto$: Observable<KoodistoDTO>;
  addKielipainotusBoolean: boolean;
  addToimintapainotusBoolean: boolean;

  constructor(
    private snackBarService: VardaSnackBarService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private koodistoService: VardaKoodistoService,
    private utilityService: VardaUtilityService
  ) {
    this.toimintapainotuksetKoodisto$ = this.koodistoService.getKoodisto(KoodistoEnum.toiminnallinenpainotus, KoodistoSortBy.name);

  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.toimipaikka?.currentValue?.id && !changes.toimipaikka?.previousValue?.id) {
      this.getKielipainotukset();
      this.getToimintapainotukset();
    }
  }

  getKielipainotukset() {
    this.vakajarjestajaApiService.getKielipainotukset(this.toimipaikka.id).subscribe({
      next: kielipainotuksetData => {
        this.kielipainotukset = kielipainotuksetData.results;
        this.utilityService.sortByAlkamisPaattymisPvm(this.kielipainotukset);
        this.toggleKielipainotukset.emit(!!this.kielipainotukset.length);
      },
      error: err => console.error(err)
    });
  }

  getToimintapainotukset() {
    this.vakajarjestajaApiService.getToimintapainotukset(this.toimipaikka.id).subscribe({
      next: toimintapainotuksetData => {
        this.toimintapainotukset = toimintapainotuksetData.results;
        this.utilityService.sortByAlkamisPaattymisPvm(this.toimintapainotukset);
        this.toggleToimintapainotukset.emit(!!this.toimintapainotukset.length);

      },
      error: err => console.error(err)
    });
  }

  closeKielipainotus(refresh?: boolean) {
    this.addKielipainotusBoolean = false;
    if (refresh) {
      this.getKielipainotukset();
    }
  }

  closeToimintapainotus(refresh?: boolean) {
    this.addToimintapainotusBoolean = false;
    if (refresh) {
      this.getToimintapainotukset();
    }
  }


}
