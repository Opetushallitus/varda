import { Component, OnDestroy, OnInit } from '@angular/core';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaUi } from '../../../utilities/models/varda-vakajarjestaja-ui.model';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaApiService } from '../../../core/services/varda-api.service';
import { DateTime } from 'luxon';
import { ErrorTree, VardaErrorMessageService } from '../../../core/services/varda-error-message.service';
import { interval, Observable, Subscription } from 'rxjs';
import { VardaSnackBarService } from '../../../core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import {
  VardaSetPaattymisPvmDTO,
  VardaSetPaattymisPvmPostDTO
} from '../../../utilities/models/dto/varda-set-paattymis-pvm-dto.model';
import { VardaDateService } from 'varda-shared';
import { ReportStatus } from '../../../utilities/models/enums/report-status.enum';

@Component({
    selector: 'app-varda-set-paattymis-pvm',
    templateUrl: './varda-set-paattymis-pvm.component.html',
    styleUrls: ['./varda-set-paattymis-pvm.component.css'],
    standalone: false
})
export class VardaSetPaattymisPvmComponent implements OnInit, OnDestroy {
  errors: Observable<Array<ErrorTree>>;
  i18n = VirkailijaTranslations;

  selectedVakajarjestaja: VardaVakajarjestajaUi;
  date: DateTime = DateTime.now();
  isLoading = false;
  isConfirmed = false;
  params: VardaSetPaattymisPvmPostDTO;
  result: VardaSetPaattymisPvmDTO;
  datasource: Array<{name: string; value: number}> = [];
  displayedColumns = ['name', 'value'];

  updateInterval = interval(10000);
  intervalSubscription: Subscription;
  identifier: string = null;

  private errorService: VardaErrorMessageService;

  constructor(
    private vakajarjestajaService: VardaVakajarjestajaService,
    private apiService: VardaApiService,
    private snackBarService: VardaSnackBarService,
    private translateService: TranslateService,
    private dateService: VardaDateService,
  ) { }

  ngOnInit() {
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.errors = this.errorService.initErrorList();
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();

    this.params = {
      vakajarjestaja_oid: this.selectedVakajarjestaja.organisaatio_oid,
      paattymis_pvm: this.dateService.luxonToVardaDate(this.date)
    };
  }

  confirm() {
    if (!this.date?.isValid) {
      return;
    }
    this.isConfirmed = true;
  }

  setPaattymisPvm() {
    if (!this.isConfirmed || !this.date?.isValid) {
      return;
    }

    this.params.paattymis_pvm = this.dateService.luxonToVardaDate(this.date);

    this.isLoading = true;
    this.apiService.postSetPaattymisPvm(this.params).subscribe({
      next: result => {
        this.identifier = result.identifier;
        this.intervalSubscription = this.updateInterval.subscribe(() => this.getResult());
      },
      error: error => {
        this.errorService.handleError(error, this.snackBarService);
        this.reset();
      }
    });
  }

  getResult() {
    this.intervalSubscription?.unsubscribe();

    this.apiService.getSetPaattymisPvm(this.identifier).subscribe({
      next: result => {
        if (result.status !== ReportStatus.FINISHED) {
          this.intervalSubscription = this.updateInterval.subscribe(() => this.getResult());
        } else {
          this.result = result;
          this.datasource = [
            [this.i18n.toimipaikka_plural, result.toimipaikka],
            [this.i18n.toimipaikka_kielipainotus_plural, result.kielipainotus],
            [this.i18n.toimipaikka_toiminnallinen_painotus_plural, result.toiminnallinenpainotus],
            [this.i18n.varhaiskasvatuspaatokset, result.varhaiskasvatuspaatos],
            [this.i18n.varhaiskasvatussuhde_plural, result.varhaiskasvatussuhde],
            [this.i18n.maksutiedot, result.maksutieto],
            [this.i18n.palvelussuhteet, result.palvelussuhde],
            [this.i18n.tyoskentelypaikka_plural, result.tyoskentelypaikka]
          ].map(item => ({name: item[0] as string, value: item[1] as number}));
          this.isLoading = false;
          this.isConfirmed = false;
        }
      },
      error: error => {
        this.errorService.handleError(error, this.snackBarService);
        this.reset();
      }
    });
  }

  getUIDate(luxonDate: DateTime) {
    return this.dateService.luxonToUiDate(luxonDate);
  }

  reset() {
    this.isLoading = false;
    this.isConfirmed = false;
    this.identifier = null;
    this.datasource = [];
    this.result = null;
    this.intervalSubscription?.unsubscribe();
  }

  ngOnDestroy() {
    this.intervalSubscription?.unsubscribe();
  }
}
