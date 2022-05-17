import { Component, Input, Output, ViewChildren, EventEmitter, ElementRef, QueryList, OnInit } from '@angular/core';
import { FormGroup, FormControl, Validators, FormArray } from '@angular/forms';
import * as moment from 'moment';
import { Moment } from 'moment';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaFormValidators } from 'projects/virkailija-app/src/app/shared/validators/varda-form-validators';
import {
  HuoltajaSaveDTO,
  VardaMaksutietoSaveDTO
} from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { finalize, Observable } from 'rxjs';
import { filter, distinctUntilChanged } from 'rxjs/operators';
import { VardaKoodistoService, VardaDateService } from 'varda-shared';
import { KoodistoDTO, KoodistoEnum } from 'projects/varda-shared/src/lib/models/koodisto-models';
import { VardaMaksutietoHuoltajaComponent } from './varda-maksutieto-huoltaja/varda-maksutieto-huoltaja.component';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import { LapsiKoosteMaksutieto } from '../../../../../../utilities/models/dto/varda-henkilohaku-dto.model';

@Component({
  selector: 'app-varda-maksutieto',
  templateUrl: './varda-maksutieto.component.html',
  styleUrls: [
    './varda-maksutieto.component.css',
    '../varda-maksutiedot.component.css',
    '../../varda-lapsi-form.component.css',
    '../../../varda-henkilo-form.component.css'
  ]
})
export class VardaMaksutietoComponent extends VardaFormAccordionAbstractComponent<LapsiKoosteMaksutieto> implements OnInit {
  @ViewChildren(VardaMaksutietoHuoltajaComponent) huoltajaElements: QueryList<VardaMaksutietoHuoltajaComponent>;
  @Input() toimipaikkaAccess: UserAccess;
  @Input() yksityinenBoolean: boolean;
  @Output() addObject = new EventEmitter<LapsiKoosteMaksutieto>(true);
  @Output() deleteObject = new EventEmitter<number>(true);

  element: ElementRef;
  huoltajat: FormArray;
  maksutietoFormErrors: Observable<Array<ErrorTree>>;
  maksunperusteKoodisto: KoodistoDTO;
  huoltajaSaveStatus: { success: number; failure: number };
  minEndDate: Date;
  disableForMaksuttomuus = false;
  koodistoEnum = KoodistoEnum;

  private errorMessageService: VardaErrorMessageService;

  constructor(
    private el: ElementRef,
    private lapsiService: VardaLapsiService,
    private koodistoService: VardaKoodistoService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService,
    modalService: VardaModalService
  ) {
    super(modalService);
    this.element = this.el;
    this.errorMessageService = new VardaErrorMessageService(translateService);
    this.maksutietoFormErrors = this.errorMessageService.initErrorList();
  }

  ngOnInit() {
    super.ngOnInit();

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true)),
      this.koodistoService.getKoodisto(KoodistoEnum.maksunperuste).subscribe(koodisto =>
        this.maksunperusteKoodisto = koodisto)
    );
  }

  initForm() {
    this.formGroup = new FormGroup({
      id: new FormControl(this.currentObject?.id),
      lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
      lapsi: new FormControl(this.lapsiService.getLapsiUrl(this.lapsiService.activeLapsi.getValue().id)),
      alkamis_pvm: new FormControl(this.currentObject?.alkamis_pvm ? moment(this.currentObject?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.currentObject?.paattymis_pvm ? moment(this.currentObject?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
      maksun_peruste_koodi: new FormControl(this.currentObject?.maksun_peruste_koodi.toLocaleUpperCase(), [Validators.required]),
      palveluseteli_arvo: new FormControl(this.currentObject?.palveluseteli_arvo, [Validators.min(0), Validators.max(9999), Validators.pattern('^\\d+([,.]\\d{1,2})?$')]),
      asiakasmaksu: new FormControl(this.currentObject?.asiakasmaksu, [Validators.required, Validators.min(0), Validators.max(9999), Validators.pattern('^\\d+([,.]\\d{1,2})?$')]),
      perheen_koko: new FormControl(this.currentObject?.perheen_koko, this.yksityinenBoolean ? null : [Validators.required, Validators.min(2), Validators.max(50)]),
      huoltajat: new FormArray([], this.currentObject ? null : Validators.required)
    });

    this.huoltajat = this.formGroup.get('huoltajat') as FormArray;
    if (this.objectExists()) {
      this.checkFormErrors(this.lapsiService, 'maksutieto', this.currentObject.id);
    } else {
      if (this.currentObject?.huoltajat.length > 0) {
        this.currentObject.huoltajat.forEach(huoltaja => this.addHuoltaja(huoltaja));
      } else {
        this.addHuoltaja();
      }
    }
  }

  saveMaksutieto(form: FormGroup): void {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.errorMessageService.resetErrorList();

    if (this.huoltajat.invalid) {
      this.disableSubmit();
      setTimeout(() => this.huoltajaElements.first.element.nativeElement.scrollIntoView({ behavior: 'smooth' }), 100);
    } else if (VardaErrorMessageService.formIsValid(form)) {
      const maksutietoDTO: VardaMaksutietoSaveDTO = {
        ...form.value,
        alkamis_pvm: form.value.alkamis_pvm?.format(VardaDateService.vardaApiDateFormat) || this.currentObject?.alkamis_pvm,
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      if (this.objectExists()) {
        // Fill huoltajat_add field for update request
        maksutietoDTO.huoltajat_add = maksutietoDTO.huoltajat || [];
        if (maksutietoDTO.huoltajat_add.length === 0) {
          delete maksutietoDTO.huoltajat_add;
        }
        delete maksutietoDTO.huoltajat;
      }

      const observable = this.objectExists() ? this.lapsiService.updateMaksutieto(maksutietoDTO) :
        this.lapsiService.createMaksutieto(maksutietoDTO);
      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            this.huoltajaSaveStatus = {
              success: result.tallennetut_huoltajat_count,
              failure: result.ei_tallennetut_huoltajat_count
            };
            this.snackBarService.success(this.i18n.maksutieto_save_success);
            this.disableForm();

            this.currentObject = result;
            setTimeout(() => {
              this.huoltajaSaveStatus = null;
              this.togglePanel(false);
              this.lapsiService.sendLapsiListUpdate();
              this.addObject.emit(this.currentObject);
            }, 5000);
          },
          error: err => this.errorMessageService.handleError(err, this.snackBarService)
        })
      );
    } else {
      this.disableSubmit();
    }
  }

  deleteMaksutieto(): void {
    this.subscriptions.push(
      this.lapsiService.deleteMaksutieto(this.currentObject.id).subscribe({
        next: () => {
          this.togglePanel(false);
          this.snackBarService.warning(this.i18n.maksutieto_delete_success);
          this.lapsiService.sendLapsiListUpdate();
          this.deleteObject.emit(this.currentObject.id);
        },
        error: err => this.errorMessageService.handleError(err, this.snackBarService)
      })
    );
  }

  enableForm() {
    super.enableForm();

    if (this.objectExists()) {
      this.formGroup.controls.huoltajat.disable();
      this.formGroup.controls.alkamis_pvm.disable();
      this.formGroup.controls.maksun_peruste_koodi.disable();
      this.formGroup.controls.palveluseteli_arvo.disable();
      this.formGroup.controls.asiakasmaksu.disable();
      this.formGroup.controls.perheen_koko.disable();
    }
    if (this.yksityinenBoolean) {
      this.formGroup.controls.palveluseteli_arvo.disable();
      this.formGroup.controls.perheen_koko.disable();
    }
  }

  removeHuoltajaForm(index: number) {
    this.huoltajat.removeAt(index);
  }

  addHuoltaja(huoltaja?: HuoltajaSaveDTO) {
    const huoltajaGroup = new FormGroup({
      addWithSsnOrOid: new FormControl(huoltaja === undefined ? true : !!huoltaja?.henkilotunnus),
      henkilotunnus: new FormControl(huoltaja?.henkilotunnus, [Validators.required, VardaFormValidators.validSSN]),
      henkilo_oid: new FormControl(huoltaja?.henkilo_oid, [Validators.required, VardaFormValidators.validOppijanumero]),
      etunimet: new FormControl(huoltaja?.etunimet, [Validators.required, VardaFormValidators.validHenkiloName]),
      sukunimi: new FormControl(huoltaja?.sukunimi, [Validators.required, VardaFormValidators.validHenkiloName])
    });

    huoltajaGroup.markAsDirty();
    this.huoltajat.push(huoltajaGroup);
  }

  changeMaksunPeruste(maksunperusteKoodi: string) {
    const palveluseteli = this.formGroup.get('palveluseteli_arvo');
    const asiakasmaksu = this.formGroup.get('asiakasmaksu');
    if (maksunperusteKoodi.toLocaleUpperCase() === 'MP01') {
      palveluseteli.setValue(0);
      asiakasmaksu.setValue(0);
      this.disableForMaksuttomuus = true;
    } else {
      palveluseteli.setValue(null);
      asiakasmaksu.setValue(null);
      this.disableForMaksuttomuus = false;
    }
  }

  startDateChange(startDate: Moment) {
    this.minEndDate = startDate?.clone().toDate();
    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }
}
