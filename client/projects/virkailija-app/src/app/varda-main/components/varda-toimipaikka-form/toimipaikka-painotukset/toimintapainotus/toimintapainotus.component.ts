import { Component, OnInit } from '@angular/core';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaApiService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja-api.service';
import { ToiminnallinenPainotusDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { KoodistoDTO, KoodistoEnum, KoodistoSortBy, VardaDateService, VardaKoodistoService } from 'varda-shared';
import { PainotusAbstractComponent } from '../painotus.abstract';
import { VardaModalService } from '../../../../../core/services/varda-modal.service';
import { finalize } from 'rxjs';

@Component({
  selector: 'app-toimintapainotus',
  templateUrl: './toimintapainotus.component.html',
  styleUrls: [
    './toimintapainotus.component.css',
    '../toimipaikka-painotukset.component.css',
    '../../varda-toimipaikka-form.component.css'
  ]
})
export class ToimintapainotusComponent extends PainotusAbstractComponent<ToiminnallinenPainotusDTO> implements OnInit {
  toiminnallinenPainotusKoodisto: KoodistoDTO;

  constructor(
    protected translateService: TranslateService,
    protected vakajarjestajaApiService: VardaVakajarjestajaApiService,
    protected snackBarService: VardaSnackBarService,
    private koodistoService: VardaKoodistoService,
    modalService: VardaModalService,
  ) {
    super(translateService, vakajarjestajaApiService, snackBarService, modalService);
  }

  ngOnInit() {
    super.ngOnInit();
    this.subscriptions.push(
      this.koodistoService.getKoodisto(KoodistoEnum.toiminnallinenpainotus, KoodistoSortBy.name).subscribe(result =>
        this.toiminnallinenPainotusKoodisto = result)
    );
  }

  initForm() {
    this.formGroup = new FormGroup({
      lahdejarjestelma: new FormControl(this.painotus?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      id: new FormControl(this.painotus?.id),
      toimintapainotus_koodi: new FormControl(this.painotus?.toimintapainotus_koodi, Validators.required),
      alkamis_pvm: new FormControl(this.painotus ? moment(this.painotus?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(
        this.painotus?.paattymis_pvm ? moment(this.painotus?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null,
        this.toimipaikka?.paattymis_pvm ? Validators.required : null
      ),
    });

    this.checkFormErrors(this.vakajarjestajaApiService, 'toiminnallinenpainotus', this.painotus?.id);
  }

  savePainotus(form: FormGroup, wasPending?: boolean) {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.errorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const painotusJson: ToiminnallinenPainotusDTO = {
        ...form.value,
        toimipaikka: this.toimipaikka?.id ? this.vakajarjestajaApiService.getToimipaikkaUrl(this.toimipaikka.id) : null,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.format(VardaDateService.vardaApiDateFormat) || null
      };

      if (!this.toimipaikka?.id) {
        this.savePending = true;
        this.painotus = { ...painotusJson };
        return this.disableForm();
      }

      const observable = this.painotus && !wasPending ? this.vakajarjestajaApiService.updateToimintapainotus(painotusJson) :
        this.vakajarjestajaApiService.createToimintapainotus(painotusJson);
      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            if (!this.painotus || wasPending) {
              // Close panel if object was created
              this.togglePanel(false);
            }

            this.snackBarService.success(this.i18n.painotukset_toimintapainotus_save_success);
            this.vakajarjestajaApiService.sendToimipaikkaListUpdate();
            this.painotus = result;
            this.addObject.emit(this.painotus);
          },
          error: err => {
            this.errorService.handleError(err, this.snackBarService);
            if (wasPending) {
              this.enableForm();
            }
          }
        })
      );
    } else {
      this.disableSubmit();
    }
  }

  deletePainotus() {
    this.subscriptions.push(
      this.vakajarjestajaApiService.deleteToimintapainotus(this.painotus.id).subscribe({
        next: () => {
          this.togglePanel(false);
          this.snackBarService.warning(this.i18n.painotukset_toimintapainotus_delete_success);
          this.vakajarjestajaApiService.sendToimipaikkaListUpdate();
          this.deleteObject.emit(this.painotus.id);
        },
        error: err => this.errorService.handleError(err, this.snackBarService)
      })
    );
  }
}
