import { Component, Input, OnInit } from '@angular/core';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaApiService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja-api.service';
import { ToiminnallinenPainotusDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { KoodistoDTO } from 'varda-shared';
import { VardaDateService } from '../../../../services/varda-date.service';
import { PainotusAbstractComponent } from '../painotus.abstract';

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
  @Input() toimintakoodisto: KoodistoDTO;

  constructor(
    protected translateService: TranslateService,
    protected vakajarjestajaApiService: VardaVakajarjestajaApiService,
    protected snackBarService: VardaSnackBarService
  ) {
    super(translateService, vakajarjestajaApiService, snackBarService);
  }

  ngOnInit(): void {
  }

  initForm() {
    this.painotusForm = new FormGroup({
      lahdejarjestelma: new FormControl(this.painotus?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      id: new FormControl(this.painotus?.id),
      toimipaikka: new FormControl(this.toimipaikka?.url),
      toimintapainotus_koodi: new FormControl(this.painotus?.toimintapainotus_koodi, Validators.required),
      alkamis_pvm: new FormControl(this.painotus ? moment(this.painotus?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(
        this.painotus?.paattymis_pvm ? moment(this.painotus?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null,
        this.toimipaikka?.paattymis_pvm ? Validators.required : null
      ),
    });
  }

  deletePainotus() {
    this.vakajarjestajaApiService.deleteToimintapainotus(this.painotus.id).subscribe({
      next: deleted => {
        this.togglePanel(false, true);
        this.snackBarService.warning(this.i18n.painotukset_toimintapainotus_delete_success);
      },
      error: err => this.errorService.handleError(err, this.snackBarService)
    });
  }

  savePainotus(form: FormGroup, wasPending?: boolean) {
    this.isSubmitting.next(true);
    form.markAllAsTouched();
    this.errorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const toimintapainotusJson: ToiminnallinenPainotusDTO = {
        ...form.value,
        toimipaikka: this.toimipaikka?.url,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.format(VardaDateService.vardaApiDateFormat) || null
      };

      if (!this.toimipaikka?.id) {
        this.savePending = true;
        this.painotus = { ...toimintapainotusJson };
        return this.disableForm();
      }

      const updatePainotus = this.painotus ? this.vakajarjestajaApiService.updateToimintapainotus(toimintapainotusJson) : this.vakajarjestajaApiService.createToimintapainotus(toimintapainotusJson);

      updatePainotus.subscribe({
        next: toimintapainotusData => {
          this.togglePanel(false, true);
          this.snackBarService.success(this.i18n.painotukset_toimintapainotus_save_success);
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
