import { Component, Input, OnInit } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { TranslateService } from '@ngx-translate/core';
import { DateTime } from 'luxon';
import { VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaApiService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja-api.service';
import { KielipainotusDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { CodeDTO, VardaDateService } from 'varda-shared';
import { PainotusAbstractComponent } from '../painotus.abstract';
import { VardaModalService } from '../../../../../core/services/varda-modal.service';
import { finalize } from 'rxjs';
import { VardaUtilityService } from '../../../../../core/services/varda-utility.service';
import { ModelNameEnum } from '../../../../../utilities/models/enums/model-name.enum';

@Component({
    selector: 'app-kielipainotus',
    templateUrl: './kielipainotus.component.html',
    styleUrls: [
        './kielipainotus.component.css',
        '../toimipaikka-painotukset.component.css',
        '../../varda-toimipaikka-form.component.css'
    ],
    standalone: false
})
export class KielipainotusComponent extends PainotusAbstractComponent<KielipainotusDTO> implements OnInit {
  @Input() kielikoodisto: Array<CodeDTO>;
  @Input() kielipainotustyyppikoodisto: Array<CodeDTO>;

  modelName = ModelNameEnum.KIELIPAINOTUS;

  constructor(
    protected translateService: TranslateService,
    protected vakajarjestajaApiService: VardaVakajarjestajaApiService,
    protected snackBarService: VardaSnackBarService,
    utilityService: VardaUtilityService,
    modalService: VardaModalService
  ) {
    super(translateService, vakajarjestajaApiService, snackBarService, modalService, utilityService);
  }

  ngOnInit() {
    super.ngOnInit();
  }

  initForm() {
    this.formGroup = new FormGroup({
      lahdejarjestelma: new FormControl(this.currentObject?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      id: new FormControl(this.currentObject?.id),
      kielipainotus_koodi: new FormControl(this.currentObject?.kielipainotus_koodi, Validators.required),
      kielipainotustyyppi_koodi: new FormControl(this.currentObject?.kielipainotustyyppi_koodi, Validators.required),
      alkamis_pvm: new FormControl(
        this.currentObject?.alkamis_pvm
          ? DateTime.fromFormat(this.currentObject.alkamis_pvm, VardaDateService.vardaApiDateFormat, VardaDateService.uiDateTimezone)
          : null,
        Validators.required
      ),
      paattymis_pvm: new FormControl(
        this.currentObject?.paattymis_pvm
          ? DateTime.fromFormat(this.currentObject.paattymis_pvm, VardaDateService.vardaApiDateFormat, VardaDateService.uiDateTimezone)
          : null,
        this.toimipaikka?.paattymis_pvm ? Validators.required : null
      ),
    });

    this.initDateFilters();
  }

  savePainotus(form: FormGroup, wasPending?: boolean) {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.errorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const painotusJson: KielipainotusDTO = {
        ...form.value,
        toimipaikka: this.toimipaikka?.id ? this.vakajarjestajaApiService.getToimipaikkaUrl(this.toimipaikka.id) : null,
        alkamis_pvm: form.value.alkamis_pvm.toFormat(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.toFormat(VardaDateService.vardaApiDateFormat) || null
      };

      if (!this.toimipaikka?.id) {
        this.savePending = true;
        this.currentObject = { ...painotusJson };
        return this.disableForm();
      }

      const observable = this.currentObject && !wasPending ? this.vakajarjestajaApiService.updateKielipainotus(painotusJson) :
        this.vakajarjestajaApiService.createKielipainotus(painotusJson);
      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            if (!this.currentObject || wasPending) {
              // Close panel if object was created
              this.togglePanel(false);
            }

            this.snackBarService.success(this.i18n.painotukset_kielipainotus_save_success);
            this.vakajarjestajaApiService.sendToimipaikkaListUpdate();
            this.currentObject = result;
            this.addObject.emit(this.currentObject);
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
      this.vakajarjestajaApiService.deleteKielipainotus(this.currentObject.id).subscribe({
        next: () => {
          this.togglePanel(false);
          this.snackBarService.warning(this.i18n.painotukset_kielipainotus_delete_success);
          this.vakajarjestajaApiService.sendToimipaikkaListUpdate();
          this.deleteObject.emit(this.currentObject.id);
        },
        error: err => this.errorService.handleError(err, this.snackBarService)
      })
    );
  }
}
