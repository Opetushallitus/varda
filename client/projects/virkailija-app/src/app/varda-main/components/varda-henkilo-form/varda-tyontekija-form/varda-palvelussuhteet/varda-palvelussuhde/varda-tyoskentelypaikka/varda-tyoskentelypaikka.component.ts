import { Component, EventEmitter, Inject, Input, OnInit, Output } from '@angular/core';
import { SaveAccess, UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import * as moment from 'moment';
import { Moment } from 'moment';
import { DOCUMENT } from '@angular/common';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { KoodistoSortBy, VardaDateService, VardaKoodistoService, KoodistoDTO, KoodistoEnum } from 'varda-shared';
import {
  ErrorTree,
  VardaErrorMessageService
} from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { finalize, Observable } from 'rxjs';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import {
  TyontekijaPalvelussuhde,
  TyontekijaTyoskentelypaikka
} from '../../../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaTyoskentelypaikkaDTO } from '../../../../../../../utilities/models/dto/varda-tyontekija-dto.model';
import { VardaUtilityService } from '../../../../../../../core/services/varda-utility.service';
import { ModelNameEnum } from '../../../../../../../utilities/models/enums/model-name.enum';

@Component({
  selector: 'app-varda-tyoskentelypaikka',
  templateUrl: './varda-tyoskentelypaikka.component.html',
  styleUrls: [
    './varda-tyoskentelypaikka.component.css',
    '../varda-palvelussuhde.component.css',
    '../../../varda-tyontekija-form.component.css',
    '../../../../varda-henkilo-form.component.css'
  ]
})
export class VardaTyoskentelypaikkaComponent extends VardaFormAccordionAbstractComponent<TyontekijaTyoskentelypaikka> implements OnInit {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() palvelussuhde: TyontekijaPalvelussuhde;
  @Output() addObject = new EventEmitter<TyontekijaTyoskentelypaikka>(true);
  @Output() deleteObject = new EventEmitter<number>(true);

  toimijaAccess: UserAccess;
  tehtavanimikkeet: KoodistoDTO;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  startDateRange = { min: null, max: null };
  endDateRange = { min: null, max: null };
  koodistoEnum = KoodistoEnum;
  palvelussuhdeFormErrors: Observable<Array<ErrorTree>>;
  modelName = ModelNameEnum.TYOSKENTELYPAIKKA;

  private henkilostoErrorService: VardaErrorMessageService;

  constructor(
    @Inject(DOCUMENT) private document,
    private authService: AuthService,
    private henkilostoService: VardaHenkilostoApiService,
    private koodistoService: VardaKoodistoService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private snackBarService: VardaSnackBarService,
    private dateService: VardaDateService,
    utilityService: VardaUtilityService,
    translateService: TranslateService,
    modalService: VardaModalService
  ) {
    super(modalService, utilityService);
    this.apiService = this.henkilostoService;
    this.toimijaAccess = this.authService.getUserAccess();
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.palvelussuhdeFormErrors = this.henkilostoErrorService.initErrorList();
  }

  ngOnInit() {
    super.ngOnInit();

    if (this.toimipaikkaAccess.tyontekijatiedot.tallentaja) {
      this.toimipaikat = this.authService.getAuthorizedToimipaikat(this.vardaVakajarjestajaService.getFilteredToimipaikat().tallentajaToimipaikat, SaveAccess.tyontekijatiedot);
      this.toimipaikat = this.toimipaikat.filter(toimipaikka => toimipaikka.organisaatio_oid);
    } else {
      this.toimipaikat = this.vardaVakajarjestajaService.getFilteredToimipaikat().toimipaikat;
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
      palvelussuhde: new FormControl(this.henkilostoService.getPalvelussuhdeUrl(this.palvelussuhde.id)),
      toimipaikka_oid: new FormControl(this.currentObject?.toimipaikka_oid || this.henkilonToimipaikka?.organisaatio_oid),
      kiertava_tyontekija_kytkin: new FormControl(this.currentObject?.kiertava_tyontekija_kytkin || false, Validators.required),
      alkamis_pvm: new FormControl(this.dateService.vardaDateToMoment(this.currentObject?.alkamis_pvm), Validators.required),
      paattymis_pvm: new FormControl(this.objectExists() ? this.dateService.vardaDateToMoment(this.currentObject?.paattymis_pvm) :
        this.dateService.vardaDateToMoment(this.palvelussuhde.paattymis_pvm)),
      tehtavanimike_koodi: new FormControl(this.currentObject?.tehtavanimike_koodi, Validators.required),
      kelpoisuus_kytkin: new FormControl(this.currentObject?.kelpoisuus_kytkin, Validators.required),
    });

    this.initDateFilters();
  }

  saveTyoskentelypaikka(form: FormGroup): void {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (!form.valid) {
      if (form.controls.kiertava_tyontekija_kytkin.value) {
        form.get('toimipaikka_oid').setValue(null);
      } else if (!form.controls.toimipaikka_oid.value) {
        form.controls.toimipaikka_oid.setErrors({ required: true });
      }

      VardaErrorMessageService.formIsValid(form);
      this.disableSubmit();
    } else {
      const tyoskentelypaikkaJson: VardaTyoskentelypaikkaDTO = {
        ...form.value,
        kiertava_tyontekija_kytkin: form.controls.kiertava_tyontekija_kytkin.value,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      if (tyoskentelypaikkaJson.kiertava_tyontekija_kytkin) {
        delete tyoskentelypaikkaJson.toimipaikka_oid;
      }

      const observable = this.currentObject ? this.henkilostoService.updateTyoskentelypaikka(tyoskentelypaikkaJson) :
        this.henkilostoService.createTyoskentelypaikka(tyoskentelypaikkaJson);
      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            if (!this.currentObject) {
              // Close panel if object was created
              this.togglePanel(false);
            }
            this.snackBarService.success(this.i18n.tyoskentelypaikka_save_success);
            this.henkilostoService.sendHenkilostoListUpdate();

            const selectedToimipaikka = this.toimipaikat.find(toimipaikka => toimipaikka.organisaatio_oid === result.toimipaikka_oid);
            this.currentObject = {...result, toimipaikka_id: selectedToimipaikka?.id,
              toimipaikka_nimi: selectedToimipaikka?.nimi};
            this.addObject.emit(this.currentObject);
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        })
      );
    }
  }

  deleteTyoskentelypaikka(): void {
    this.subscriptions.push(
      this.henkilostoService.deleteTyoskentelypaikka(this.currentObject.id).subscribe({
        next: () => {
          this.togglePanel(false);
          this.snackBarService.warning(this.i18n.tyoskentelypaikka_delete_success);
          this.henkilostoService.sendHenkilostoListUpdate();
          this.deleteObject.emit(this.currentObject.id);
        },
        error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
      })
    );
  }

  enableForm() {
    super.enableForm();

    setTimeout(() => {
      if (this.currentObject) {
        this.formGroup.controls.kiertava_tyontekija_kytkin.disable();
        this.formGroup.controls.toimipaikka_oid.disable();
      }
      if (!this.toimijaAccess.tyontekijatiedot.tallentaja) {
        this.formGroup.controls.kiertava_tyontekija_kytkin.disable();
      }
    });
  }

  initDateFilters() {
    this.startDateRange.min = new Date(this.palvelussuhde.alkamis_pvm);
    this.startDateChange(this.formGroup.controls.alkamis_pvm?.value);

    if (this.palvelussuhde.paattymis_pvm) {
      this.startDateRange.max = new Date(this.palvelussuhde.paattymis_pvm);
      this.endDateRange.max = new Date(this.palvelussuhde.paattymis_pvm);
    }
  }

  startDateChange(startDate: Moment) {
    this.endDateRange.min = startDate?.clone().toDate() || new Date(this.palvelussuhde.alkamis_pvm);
    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }
}
