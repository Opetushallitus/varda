import { Component, ElementRef, EventEmitter, Input, OnDestroy, OnInit, Output, ViewChild } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { MatCheckboxChange } from '@angular/material/checkbox';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { Moment } from 'moment';
import { finalize, Observable, Subscription } from 'rxjs';
import { distinctUntilChanged, filter, map, take } from 'rxjs/operators';
import { VardaDateService, VardaKoodistoService, CodeDTO, KoodistoEnum, KoodistoSortBy } from 'varda-shared';
import { AuthService } from '../../../core/auth/auth.service';
import { ErrorTree, VardaErrorMessageService } from '../../../core/services/varda-error-message.service';
import { VardaSnackBarService } from '../../../core/services/varda-snackbar.service';
import { VardaVakajarjestajaApiService } from '../../../core/services/varda-vakajarjestaja-api.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaFormValidators } from '../../../shared/validators/varda-form-validators';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import {
  ToimipaikkaKooste,
  VardaToimipaikkaDTO,
  VardaToimipaikkaMinimalDto
} from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { Hallinnointijarjestelma, Lahdejarjestelma } from '../../../utilities/models/enums/hallinnointijarjestelma';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { VardaFormAccordionAbstractComponent } from '../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import { VardaModalService } from '../../../core/services/varda-modal.service';
import { VardaKoosteApiService } from '../../../core/services/varda-kooste-api.service';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';
import { ModelNameEnum } from '../../../utilities/models/enums/model-name.enum';

@Component({
  selector: 'app-varda-toimipaikka-form',
  templateUrl: './varda-toimipaikka-form.component.html',
  styleUrls: ['./varda-toimipaikka-form.component.css']
})
export class VardaToimipaikkaFormComponent extends VardaFormAccordionAbstractComponent<ToimipaikkaKooste> implements OnInit, OnDestroy {
  @ViewChild('formContent') formContent: ElementRef;
  @Input() toimipaikka: VardaToimipaikkaMinimalDto;
  @Output() saveToimipaikkaFormSuccess = new EventEmitter<VardaToimipaikkaDTO>(true);
  @Output() valuesChanged = new EventEmitter<boolean>(true);

  koodistoEnum = KoodistoEnum;
  toimijaAccess: UserAccess;
  tallentajaAccess: boolean;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  showFormContinuesWarning: boolean;
  toimipaikkaFormErrors: Observable<Array<ErrorTree>>;
  minEndDate: Date;
  maxEndDate: Date;
  toimintamuotoCodes: Array<CodeDTO> = [];
  kuntaCodes: Array<CodeDTO> = [];
  jarjestamismuotoCodes: Array<CodeDTO> = [];
  kasvatusopillinenCodes: Array<CodeDTO> = [];
  postitoimipaikkaCodes: Array<CodeDTO> = [];
  kielikoodisto: Array<CodeDTO>;
  postiosoiteToggleBoolean = false;
  modelName = ModelNameEnum.TOIMIPAIKKA;

  private errorService: VardaErrorMessageService;
  private formGroupSubscriptions: Array<Subscription> = [];

  constructor(
    private authService: AuthService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private snackBarService: VardaSnackBarService,
    private koodistoService: VardaKoodistoService,
    private translateService: TranslateService,
    private koosteService: VardaKoosteApiService,
    utilityService: VardaUtilityService,
    modalService: VardaModalService
  ) {
    super(modalService, utilityService);
    this.apiService = this.vakajarjestajaApiService;
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.toimijaAccess = this.authService.getUserAccess();
    this.toimipaikkaFormErrors = this.errorService.initErrorList();
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
  }

  ngOnInit() {
    this.vakajarjestajaApiService.activeToimipaikka.next(null);
    this.tallentajaAccess = this.toimijaAccess.lapsitiedot.tallentaja;
    if (this.toimipaikka?.id) {
      // User can also have Toimipaikka level tallentaja access
      this.tallentajaAccess = this.tallentajaAccess || this.authService.getUserAccess(this.toimipaikka.organisaatio_oid).lapsitiedot.tallentaja;
      if (this.toimipaikka.paos_organisaatio_url || this.toimipaikka.hallinnointijarjestelma !== Hallinnointijarjestelma.VARDA) {
        this.tallentajaAccess = false;
      }

      this.getToimipaikkaKooste();
      this.vakajarjestajaApiService.initFormErrorList(this.selectedVakajarjestaja.id, this.toimipaikka);
    } else {
      this.initForm();
    }

    // Depending on if current Vakajarjestaja is kunnallinen or yksityinen, exclude jarjestamismuoto options
    const excludeJarjestamismuotoCodes = this.vakajarjestajaService.getSelectedVakajarjestaja().kunnallinen_kytkin ? ['jm04', 'jm05'] : ['jm01'];
    this.subscriptions.push(
      this.vakajarjestajaApiService.listenToimipaikkaListUpdate().subscribe(() =>
        this.vakajarjestajaApiService.initFormErrorList(this.selectedVakajarjestaja.id, this.toimipaikka)),
      this.koodistoService.getKoodisto(KoodistoEnum.posti, KoodistoSortBy.name).subscribe(result =>
        this.postitoimipaikkaCodes = result.codes),
      this.koodistoService.getKoodisto(KoodistoEnum.toimintamuoto, KoodistoSortBy.name).subscribe(result =>
        this.toimintamuotoCodes = result.codes),
      this.koodistoService.getKoodisto(KoodistoEnum.kunta, KoodistoSortBy.name).subscribe(result =>
        this.kuntaCodes = result.codes),
      this.koodistoService.getKoodisto(KoodistoEnum.kasvatusopillinenjarjestelma, KoodistoSortBy.name).subscribe(result =>
        this.kasvatusopillinenCodes = result.codes),
      this.koodistoService.getKoodisto(KoodistoEnum.jarjestamismuoto, KoodistoSortBy.name).pipe(
        map(result =>
          result.codes.filter(code => !excludeJarjestamismuotoCodes.includes(code.code_value.toLowerCase())))
      ).subscribe(result => this.jarjestamismuotoCodes = result),
      this.koodistoService.getKoodisto(KoodistoEnum.kieli, KoodistoSortBy.name).pipe(take(1)).subscribe(kielikoodisto => {
        const languagePriority = ['FI', 'SV', 'SEPO', 'RU', 'ET', 'EN', 'AR', 'SO', 'DE', 'FR', '99'];
        const noPriority = 999;
        this.kielikoodisto = [...kielikoodisto.codes];
        this.kielikoodisto.sort((a, b) => {
          let indexA = languagePriority.indexOf(a.code_value.toLocaleUpperCase());
          let indexB = languagePriority.indexOf(b.code_value.toLocaleUpperCase());
          indexA = indexA < 0 ? noPriority : indexA;
          indexB = indexB < 0 ? noPriority : indexB;

          if (indexA < noPriority || indexB < noPriority) {
            return indexA < indexB ? -1 : 1;
          }

          return Number(b.active) - Number(a.active) || a.name.localeCompare(b.name);
        });
      })
    );
  }

  disableForm() {
    super.disableForm();

    this.valuesChanged.emit(false);
  }

  initForm() {
    this.formGroupSubscriptions.forEach(subscription => subscription.unsubscribe());
    this.formGroup = new FormGroup({
      lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
      id: new FormControl(this.currentObject?.id),
      nimi: new FormControl(this.currentObject?.nimi,
        [Validators.required, Validators.minLength(3), Validators.maxLength(200), VardaFormValidators.hasCharacters(), VardaFormValidators.rejectSpecialChars]),
      organisaatio_oid: new FormControl(this.currentObject?.organisaatio_oid),
      kayntiosoite: new FormControl(this.currentObject?.kayntiosoite,
        [Validators.required, Validators.minLength(3), Validators.maxLength(100), VardaFormValidators.hasCharacters(), VardaFormValidators.rejectSpecialChars]),
      kayntiosoite_postinumero: new FormControl(this.currentObject?.kayntiosoite_postinumero, [Validators.required]),
      kayntiosoite_postitoimipaikka: new FormControl(this.currentObject?.kayntiosoite_postitoimipaikka, [Validators.required]),
      postiosoite: new FormControl(this.currentObject?.postiosoite,
        [Validators.required, Validators.minLength(3), Validators.maxLength(100), VardaFormValidators.hasCharacters(), VardaFormValidators.rejectSpecialChars]),
      postinumero: new FormControl(this.currentObject?.postinumero, [Validators.required]),
      postitoimipaikka: new FormControl(this.currentObject?.postitoimipaikka, [Validators.required]),
      kunta_koodi: new FormControl(this.currentObject?.kunta_koodi.toLocaleUpperCase(), [Validators.required]),
      puhelinnumero: new FormControl(this.currentObject?.puhelinnumero, [Validators.required, VardaFormValidators.validStringFormat.bind(null, { regex: '^(\\+358)[1-9]\\d{5,10}$' })]),
      sahkopostiosoite: new FormControl(this.currentObject?.sahkopostiosoite, [Validators.required, VardaFormValidators.validStringFormat.bind(null, { regex: '^[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+(\\.[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+)*@[A-Za-z0-9][A-Za-z0-9-]+(\\.[A-Za-z0-9-]+)*(\\.[A-Za-z]{2,})$' })]),
      toimintamuoto_koodi: new FormControl(this.currentObject?.toimintamuoto_koodi.toLocaleUpperCase(), [Validators.required]),
      jarjestamismuoto_koodi: new FormControl(this.currentObject?.jarjestamismuoto_koodi.map(koodi => koodi.toLocaleUpperCase()), [Validators.required]),
      asiointikieli_koodi: new FormControl(this.currentObject?.asiointikieli_koodi.map(koodi => koodi.toLocaleUpperCase()), [Validators.required]),
      kasvatusopillinen_jarjestelma_koodi: new FormControl(this.currentObject?.kasvatusopillinen_jarjestelma_koodi.toLocaleUpperCase() || 'KJ98', [Validators.required]),
      varhaiskasvatuspaikat: new FormControl(this.currentObject?.varhaiskasvatuspaikat, [Validators.required, Validators.min(0)]),
      alkamis_pvm: new FormControl(this.currentObject ? moment(this.currentObject?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.currentObject?.paattymis_pvm ? moment(this.currentObject?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
      vakajarjestaja: new FormControl(this.selectedVakajarjestaja.url)
    });

    if (!this.tallentajaAccess || this.toimipaikka) {
      this.disableForm();
      if (this.toimipaikka) {
        this.checkPostiosoiteToggle();
        this.startDateChange(this.formGroup.get('alkamis_pvm')?.value);
        this.endDateChange(this.formGroup.get('paattymis_pvm')?.value);
      }
    } else {
      this.enableForm();
    }

    this.formGroupSubscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.valuesChanged.emit(true)),
      this.formGroup.get('kayntiosoite_postinumero').valueChanges.subscribe(postinumero =>
        this.changePostinumero(postinumero, true)
      ),
      this.formGroup.get('postinumero').valueChanges.subscribe(postinumero =>
        this.changePostinumero(postinumero)
      )
    );

    this.checkFormErrors();
  }

  getToimipaikkaKooste() {
    this.subscriptions.push(
      this.koosteService.getToimipaikkaKooste(this.toimipaikka?.id).subscribe({
        next: result => {
          this.currentObject = result;
          this.vakajarjestajaApiService.activeToimipaikka.next(this.currentObject);
          this.initForm();
        },
        error: err => this.errorService.handleError(err, this.snackBarService)
      })
    );
  }

  saveToimipaikka(form: FormGroup) {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.errorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const toimipaikkaDTO: VardaToimipaikkaDTO = {
        ...form.getRawValue(),
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      const observable = this.toimipaikka ? this.vakajarjestajaApiService.updateToimipaikka(toimipaikkaDTO) :
        this.vakajarjestajaApiService.createToimipaikka(toimipaikkaDTO);
      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            this.snackBarService.success(this.i18n.toimipaikka_save_success);
            this.saveToimipaikkaFormSuccess.emit(result);
            this.disableForm();

            const activeToimipaikka = this.vakajarjestajaApiService.activeToimipaikka.getValue();
            this.toimipaikka = result;
            this.vakajarjestajaApiService.sendToimipaikkaListUpdate();
            this.currentObject = {...result, vakajarjestaja_id: this.selectedVakajarjestaja.id,
              vakajarjestaja_nimi: this.selectedVakajarjestaja.nimi,
              kielipainotukset: activeToimipaikka?.kielipainotukset || [],
              toiminnalliset_painotukset: activeToimipaikka?.toiminnalliset_painotukset || []};
            this.initForm();
            this.vakajarjestajaApiService.activeToimipaikka.next(this.currentObject);
          },
          error: err => this.errorService.handleError(err, this.snackBarService)
        })
      );
    } else {
      this.disableSubmit();
    }
  }

  changePostinumero(postinumero: string, kayntiosoite?: boolean) {
    let postitoimipaikka = this.postitoimipaikkaCodes.find(code =>
      code.code_value.toLowerCase() === postinumero?.toLowerCase())?.name;
    postitoimipaikka = postitoimipaikka !== undefined ? postitoimipaikka : null;

    const formControl = kayntiosoite ? this.formGroup.get('kayntiosoite_postitoimipaikka') :
      this.formGroup.get('postitoimipaikka');
    formControl.setValue(postitoimipaikka);
    formControl.markAsTouched();
  }

  checkPostiosoiteToggle() {
    const kayntiosoite = this.formGroup.get('kayntiosoite')?.value;
    const kayntiosoitePostinumero = this.formGroup.get('kayntiosoite_postinumero')?.value;
    const kayntiosoitePostitoimipaikka = this.formGroup.get('kayntiosoite_postitoimipaikka')?.value;
    const postiosoite = this.formGroup.get('postiosoite')?.value;
    const postitoimipaikka = this.formGroup.get('postitoimipaikka')?.value;
    const postinumero = this.formGroup.get('postinumero')?.value;

    if (kayntiosoite && postiosoite && kayntiosoitePostitoimipaikka && postitoimipaikka && kayntiosoitePostinumero && postinumero) {
      this.postiosoiteToggleBoolean = kayntiosoite === postiosoite && kayntiosoitePostitoimipaikka === postitoimipaikka && kayntiosoitePostinumero === postinumero;
    } else {
      this.postiosoiteToggleBoolean = false;
    }

    if (this.postiosoiteToggleBoolean) {
      this.formGroup.get('postiosoite').disable();
      this.formGroup.get('postinumero').disable();
    } else {
      this.formGroup.get('postiosoite').enable();
      this.formGroup.get('postinumero').enable();
    }
  }

  togglePostinumero(change: MatCheckboxChange) {
    this.postiosoiteToggleBoolean = change.checked;

    if (this.postiosoiteToggleBoolean) {
      this.formGroup.get('postiosoite').disable();
      this.formGroup.get('postiosoite').setValue(this.formGroup.get('kayntiosoite').value);
      this.formGroup.get('postinumero').disable();
      this.formGroup.get('postinumero').setValue(this.formGroup.get('kayntiosoite_postinumero').value);
      this.formGroup.updateValueAndValidity();
    } else {
      this.formGroup.get('postiosoite').enable();
      this.formGroup.get('postinumero').enable();
    }
  }

  startDateChange(startDate: Moment) {
    this.minEndDate = startDate?.clone().add(1, 'days').toDate();
    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  endDateChange(endDate: Moment) {
    this.maxEndDate = endDate?.clone().toDate();
  }

  enableForm() {
    super.enableForm();
    this.checkPostiosoiteToggle();
  }

  ngOnDestroy() {
    super.ngOnDestroy();

    this.vakajarjestajaApiService.activeToimipaikka.next(null);
    this.formGroupSubscriptions.forEach(sub => sub.unsubscribe());
    this.utilityService.setFocusObjectSubject(null);
  }
}
