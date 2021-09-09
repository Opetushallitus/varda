import { Component, Input } from '@angular/core';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaApiService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja-api.service';
import { KielipainotusDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { CodeDTO, VardaDateService } from 'varda-shared';
import { PainotusAbstractComponent } from '../painotus.abstract';
import { VardaModalService } from '../../../../../core/services/varda-modal.service';
@Component({
  selector: 'app-kielipainotus',
  templateUrl: './kielipainotus.component.html',
  styleUrls: [
    './kielipainotus.component.css',
    '../toimipaikka-painotukset.component.css',
    '../../varda-toimipaikka-form.component.css'
  ]
})
export class KielipainotusComponent extends PainotusAbstractComponent<KielipainotusDTO> {
  @Input() kielikoodisto: Array<CodeDTO>;

  constructor(
    protected translateService: TranslateService,
    protected vakajarjestajaApiService: VardaVakajarjestajaApiService,
    protected snackBarService: VardaSnackBarService,
    modalService: VardaModalService,
  ) {
    super(translateService, vakajarjestajaApiService, snackBarService, modalService);
  }

  initForm() {
    this.formGroup = new FormGroup({
      lahdejarjestelma: new FormControl(this.painotus?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      id: new FormControl(this.painotus?.id),
      toimipaikka: new FormControl(this.toimipaikka?.url),
      kielipainotus_koodi: new FormControl(this.painotus?.kielipainotus_koodi, Validators.required),
      alkamis_pvm: new FormControl(this.painotus ? moment(this.painotus?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(
        this.painotus?.paattymis_pvm ? moment(this.painotus?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null,
        this.toimipaikka?.paattymis_pvm ? Validators.required : null
      ),
    });

    this.checkFormErrors(this.vakajarjestajaApiService, 'kielipainotus', this.painotus?.id);
  }

  deletePainotus() {
    this.vakajarjestajaApiService.deleteKielipainotus(this.painotus.id).subscribe({
      next: deleted => {
        this.togglePanel(false, true, true);
        this.snackBarService.warning(this.i18n.painotukset_kielipainotus_delete_success);
      },
      error: err => this.errorService.handleError(err, this.snackBarService)
    });
  }

  savePainotus(form: FormGroup, wasPending?: boolean) {
    this.isSubmitting.next(true);
    form.markAllAsTouched();
    this.errorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const kielipainotusJson: KielipainotusDTO = {
        ...form.value,
        toimipaikka: this.toimipaikka?.url,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.format(VardaDateService.vardaApiDateFormat) || null
      };

      if (!this.toimipaikka?.id) {
        this.savePending = true;
        this.painotus = { ...kielipainotusJson };
        return this.disableForm();
      }

      const updatePainotus = this.painotus ? this.vakajarjestajaApiService.updateKielipainotus(kielipainotusJson) : this.vakajarjestajaApiService.createKielipainotus(kielipainotusJson);

      updatePainotus.subscribe({
        next: kielipainotusData => {
          this.togglePanel(false, true, true);
          this.snackBarService.success(this.i18n.painotukset_kielipainotus_save_success);
        },
        error: err => {
          this.errorService.handleError(err, this.snackBarService);
          if (wasPending) {
            this.disableForm();
          }
        }
      }).add(() => this.disableSubmit());
    } else {
      this.disableSubmit();
    }
  }
}
