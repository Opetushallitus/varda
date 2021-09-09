import { Component, OnInit, Input, Output, ViewChildren, EventEmitter, ElementRef, OnDestroy, QueryList } from '@angular/core';
import { FormGroup, FormControl, Validators, FormArray } from '@angular/forms';
import * as moment from 'moment';
import { Moment } from 'moment';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaFormValidators } from 'projects/virkailija-app/src/app/shared/validators/varda-form-validators';
import { LapsiListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { VardaMaksutietoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-maksutieto-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';
import { filter, distinctUntilChanged } from 'rxjs/operators';
import { VardaKoodistoService, VardaDateService } from 'varda-shared';
import { KoodistoDTO, KoodistoEnum } from 'projects/varda-shared/src/lib/models/koodisto-models';
import { VardaMaksutietoHuoltajaComponent } from './varda-maksutieto-huoltaja/varda-maksutieto-huoltaja.component';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';


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
export class VardaMaksutietoComponent extends VardaFormAccordionAbstractComponent implements OnInit, OnDestroy {
  @Input() lapsi: LapsiListDTO;
  @Input() toimipaikkaAccess: UserAccess;
  @Input() maksutieto: VardaMaksutietoDTO;
  @Input() yksityinenBoolean: boolean;
  @Output() changedMaksutieto = new EventEmitter<boolean>(true);
  @ViewChildren(VardaMaksutietoHuoltajaComponent) huoltajaElements: QueryList<VardaMaksutietoHuoltajaComponent>;
  element: ElementRef;
  huoltajat: FormArray;
  maksutietoFormErrors: Observable<Array<ErrorTree>>;
  subscriptions: Array<Subscription> = [];
  maksunperusteKoodisto: KoodistoDTO;
  huoltajaSaveStatus: { success: number; failure: number };
  minEndDate: Date;
  disableForMaksuttomuus = false;
  isSubmitting = new BehaviorSubject<boolean>(false);
  koodistoEnum = KoodistoEnum;
  private henkilostoErrorService: VardaErrorMessageService;

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
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.maksutietoFormErrors = this.henkilostoErrorService.initErrorList();
    this.koodistoService.getKoodisto(KoodistoEnum.maksunperuste).subscribe(koodisto => this.maksunperusteKoodisto = koodisto);
  }

  ngOnInit() {
    if (!this.maksutieto) {
      this.togglePanel(true, undefined, true);
    }

    this.formGroup = new FormGroup({
      id: new FormControl(this.maksutieto?.id),
      lahdejarjestelma: new FormControl(this.maksutieto?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      lapsi: new FormControl(this.maksutieto?.lapsi || `/api/v1/lapset/${this.lapsi.id}/`),
      alkamis_pvm: new FormControl(this.maksutieto ? moment(this.maksutieto?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.maksutieto?.paattymis_pvm ? moment(this.maksutieto?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
      maksun_peruste_koodi: new FormControl(this.maksutieto?.maksun_peruste_koodi.toLocaleUpperCase(), [Validators.required]),
      palveluseteli_arvo: new FormControl(this.maksutieto?.palveluseteli_arvo, [Validators.min(0), Validators.max(9999), Validators.pattern('^\\d+([,.]\\d{1,2})?$')]),
      asiakasmaksu: new FormControl(this.maksutieto?.asiakasmaksu, [Validators.required, Validators.min(0), Validators.max(9999), Validators.pattern('^\\d+([,.]\\d{1,2})?$')]),
      perheen_koko: new FormControl(this.maksutieto?.perheen_koko, this.yksityinenBoolean ? null : [Validators.required, Validators.min(2), Validators.max(50)]),
      huoltajat: new FormArray([], Validators.required)
    });

    this.huoltajat = this.formGroup.get('huoltajat') as FormArray;
    if (!this.maksutieto) {
      this.addHuoltaja();
    } else {
      this.checkFormErrors(this.lapsiService, 'maksutieto', this.maksutieto.id);
    }

    if (!this.toimipaikkaAccess.huoltajatiedot.tallentaja || this.maksutieto) {
      this.disableForm();
    } else {
      this.enableForm();
    }

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  saveMaksutieto(form: FormGroup): void {
    this.isSubmitting.next(true);
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (this.formGroup.controls.huoltajat.invalid) {
      this.disableSubmit();
      setTimeout(() => this.huoltajaElements.first.element.nativeElement.scrollIntoView({ behavior: 'smooth' }), 100);
    } else if (VardaErrorMessageService.formIsValid(form)) {
      const maksutietoDTO: VardaMaksutietoDTO = {
        ...form.value,
        alkamis_pvm: form.value.alkamis_pvm?.format(VardaDateService.vardaApiDateFormat) || this.maksutieto?.alkamis_pvm,
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      if (this.maksutieto) {
        this.lapsiService.updateMaksutieto(maksutietoDTO).subscribe({
          next: maksutietoData => {
            this.togglePanel(false, true, true);
            this.snackBarService.success(this.i18n.maksutieto_save_success);
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      } else {
        this.lapsiService.createMaksutieto(maksutietoDTO).subscribe({
          next: maksutietoData => {
            this.huoltajaSaveStatus = {
              success: maksutietoData.tallennetut_huoltajat_count,
              failure: maksutietoData.ei_tallennetut_huoltajat_count
            };
            this.snackBarService.success(this.i18n.maksutieto_save_success);
            this.disableForm();

            setTimeout(() => {
              this.huoltajaSaveStatus = null;
              this.togglePanel(false, true, true);
            }, 5000);

          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      }
    } else {
      this.disableSubmit();
    }
  }

  deleteMaksutieto(): void {
    this.lapsiService.deleteMaksutieto(this.maksutieto.id).subscribe({
      next: deleted => {
        this.togglePanel(false, true, true);
        this.snackBarService.warning(this.i18n.maksutieto_delete_success);
      },
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting.next(false), 500);
  }

  enableForm() {
    this.isEdit = true;
    this.formGroup.enable();
    if (this.maksutieto) {
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

  addHuoltaja() {
    const huoltajaGroup = new FormGroup({
      addWithSsnOrOid: new FormControl(true),
      henkilotunnus: new FormControl(null, [Validators.required, VardaFormValidators.validSSN]),
      henkilo_oid: new FormControl(null, [Validators.required, VardaFormValidators.validOppijanumero]),
      etunimet: new FormControl(null, [Validators.required, VardaFormValidators.validHenkiloName]),
      sukunimi: new FormControl(null, [Validators.required, VardaFormValidators.validHenkiloName])
    });

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

  sendUpdateList() {
    this.lapsiService.sendLapsiListUpdate();
  }
}
