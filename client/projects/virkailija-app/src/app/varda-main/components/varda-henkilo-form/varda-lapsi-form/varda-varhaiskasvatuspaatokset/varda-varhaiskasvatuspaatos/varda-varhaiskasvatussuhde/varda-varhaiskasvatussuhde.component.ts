import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import * as moment from 'moment';
import { Moment } from 'moment';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import {
  ErrorTree,
  VardaErrorMessageService
} from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { SaveAccess, UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { finalize, Observable } from 'rxjs';
import { KoodistoDTO, KoodistoEnum, KoodistoSortBy, VardaDateService, VardaKoodistoService } from 'varda-shared';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import {
  LapsiKoosteVakapaatos,
  LapsiKoosteVakasuhde
} from '../../../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaVarhaiskasvatussuhdeDTO } from '../../../../../../../utilities/models/dto/varda-lapsi-dto.model';
import { VardaUtilityService } from '../../../../../../../core/services/varda-utility.service';
import { ModelNameEnum } from '../../../../../../../utilities/models/enums/model-name.enum';

@Component({
  selector: 'app-varda-varhaiskasvatussuhde',
  templateUrl: './varda-varhaiskasvatussuhde.component.html',
  styleUrls: [
    './varda-varhaiskasvatussuhde.component.css',
    '../varda-varhaiskasvatuspaatos.component.css',
    '../../varda-varhaiskasvatuspaatokset.component.css',
    '../../../varda-lapsi-form.component.css',
    '../../../../varda-henkilo-form.component.css'
  ]
})
export class VardaVarhaiskasvatussuhdeComponent extends VardaFormAccordionAbstractComponent<LapsiKoosteVakasuhde> implements OnInit {
  @Input() lapsitiedotTallentaja: boolean;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() varhaiskasvatuspaatos: LapsiKoosteVakapaatos;
  @Output() addObject = new EventEmitter<LapsiKoosteVakasuhde>(true);
  @Output() deleteObject = new EventEmitter<number>(true);

  toimijaAccess: UserAccess;
  tehtavanimikkeet: KoodistoDTO;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  startDateRange = { min: null, max: null };
  endDateRange = { min: null, max: null };
  varhaiskasvatussuhdeFormErrors: Observable<Array<ErrorTree>>;
  modelName = ModelNameEnum.VARHAISKASVATUSSUHDE;

  private errorMessageService: VardaErrorMessageService;

  constructor(
    private authService: AuthService,
    private lapsiService: VardaLapsiService,
    private koodistoService: VardaKoodistoService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private snackBarService: VardaSnackBarService,
    private dateService: VardaDateService,
    utilityService: VardaUtilityService,
    translateService: TranslateService,
    modalService: VardaModalService
  ) {
    super(modalService, utilityService);
    this.apiService = this.lapsiService;
    this.toimijaAccess = this.authService.getUserAccess();
    this.errorMessageService = new VardaErrorMessageService(translateService);
    this.varhaiskasvatussuhdeFormErrors = this.errorMessageService.initErrorList();
    this.initToimipaikat();
  }

  ngOnInit() {
    super.ngOnInit();

    const filteredToimipaikat = this.vardaVakajarjestajaService.getFilteredToimipaikat();
    if (this.lapsitiedotTallentaja) {
      this.toimipaikat = this.authService.getAuthorizedToimipaikat(filteredToimipaikat.tallentajaToimipaikat, SaveAccess.lapsitiedot);
      this.toimipaikat = this.toimipaikat.filter(toimipaikka => toimipaikka.organisaatio_oid);
      // remove PAOS-toimipaikat from JM01
      if (this.varhaiskasvatuspaatos.jarjestamismuoto_koodi.toLocaleUpperCase() === 'JM01') {
        this.toimipaikat = this.toimipaikat.filter(toimipaikka => !toimipaikka.paos_organisaatio_url);
      }
    } else {
      this.toimipaikat = filteredToimipaikat.toimipaikat;
    }

    const activeLapsi = this.lapsiService.activeLapsi.getValue();
    if (activeLapsi?.tallentaja_organisaatio_oid) {
      const vakajarjestajaOID = this.vardaVakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid;
      if (activeLapsi.paos_organisaatio_oid === vakajarjestajaOID) {
        this.toimipaikat = this.toimipaikat.filter(toimipaikka => !toimipaikka.paos_organisaatio_url);
      } else {
        this.toimipaikat = this.toimipaikat.filter(toimipaikka => toimipaikka.paos_organisaatio_oid === activeLapsi.paos_organisaatio_oid);
      }
    }

    this.subscriptions.push(
      this.koodistoService.getKoodisto(KoodistoEnum.tehtavanimike, KoodistoSortBy.name).subscribe(koodisto =>
        this.tehtavanimikkeet = koodisto)
    );
  }

  initForm() {
    this.formGroup = new FormGroup({
      id: new FormControl(this.currentObject?.id),
      lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
      varhaiskasvatuspaatos: new FormControl(this.lapsiService.getVarhaiskasvatuspaatosUrl(this.varhaiskasvatuspaatos.id), Validators.required),
      alkamis_pvm: new FormControl(this.currentObject ? moment(this.currentObject?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.objectExists() ? this.dateService.vardaDateToMoment(this.currentObject?.paattymis_pvm) :
          this.dateService.vardaDateToMoment(this.varhaiskasvatuspaatos.paattymis_pvm),
        this.varhaiskasvatuspaatos.paattymis_pvm ? [Validators.required] : null),
      toimipaikka_oid: new FormControl(this.currentObject?.toimipaikka_oid || this.henkilonToimipaikka?.organisaatio_oid, Validators.required),
    });

    this.initDateFilters();
  }

  saveVarhaiskasvatussuhde(form: FormGroup): void {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.errorMessageService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const varhaiskasvatussuhdeJson: VardaVarhaiskasvatussuhdeDTO = {
        ...form.value,
        toimipaikka_oid: form.value.toimipaikka_oid || this.currentObject.toimipaikka_oid,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      const observable = this.currentObject ? this.lapsiService.updateVarhaiskasvatussuhde(varhaiskasvatussuhdeJson) :
        this.lapsiService.createVarhaiskasvatussuhde(varhaiskasvatussuhdeJson);
      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            if (!this.currentObject) {
              // Close panel if object was created
              this.togglePanel(false);
            }

            this.snackBarService.success(this.i18n.varhaiskasvatussuhde_save_success);
            this.lapsiService.sendLapsiListUpdate();
            this.currentObject = {...result, toimipaikka_nimi: ''};
            this.addObject.emit(this.currentObject);
          },
          error: err => this.errorMessageService.handleError(err, this.snackBarService)
        })
      );
    } else {
      this.disableSubmit();
    }
  }

  deleteVarhaiskasvatussuhde(): void {
    this.subscriptions.push(
      this.lapsiService.deleteVarhaiskasvatussuhde(this.currentObject.id).subscribe({
        next: () => {
          this.togglePanel(false);
          this.snackBarService.warning(this.i18n.varhaiskasvatussuhde_delete_success);
          this.lapsiService.sendLapsiListUpdate();
          this.deleteObject.emit(this.currentObject.id);
        },
        error: err => this.errorMessageService.handleError(err, this.snackBarService)
      })
    );
  }

  enableForm() {
    super.enableForm();

    setTimeout(() => {
      if (this.currentObject) {
        this.formGroup.controls.toimipaikka_oid.disable();
      }
    });
  }

  initToimipaikat() {
    const { toimipaikat, tallentajaToimipaikat } = this.vardaVakajarjestajaService.getFilteredToimipaikat();
    if (this.currentObject && !this.toimijaAccess.lapsitiedot.tallentaja) {
      this.toimipaikat = toimipaikat;
    } else {
      this.toimipaikat = tallentajaToimipaikat.filter(toimipaikka => {
        const access = this.authService.getUserAccess(toimipaikka.organisaatio_oid);
        return access.lapsitiedot.tallentaja;
      });
    }
  }

  initDateFilters() {
    if (this.varhaiskasvatuspaatos) {
      this.startDateRange.min = new Date(this.varhaiskasvatuspaatos.alkamis_pvm);
      this.startDateChange(this.formGroup.controls.alkamis_pvm?.value);

      if (this.varhaiskasvatuspaatos.paattymis_pvm) {
        this.startDateRange.max = new Date(this.varhaiskasvatuspaatos.paattymis_pvm);
        this.endDateRange.max = new Date(this.varhaiskasvatuspaatos.paattymis_pvm);
      }
    }
  }

  startDateChange(startDate: Moment) {
    this.endDateRange.min = startDate?.clone().toDate() || new Date(this.varhaiskasvatuspaatos.alkamis_pvm);
    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }
}
