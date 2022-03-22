import { Component, ElementRef, EventEmitter, Input, OnDestroy, OnInit, Output, ViewChild } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { MatCheckboxChange } from '@angular/material/checkbox';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { Moment } from 'moment';
import { finalize, Observable, Subscription } from 'rxjs';
import { distinctUntilChanged, filter, map, take } from 'rxjs/operators';
import { VardaKoodistoService, VardaDateService } from 'varda-shared';
import { CodeDTO, KoodistoDTO, KoodistoEnum, KoodistoSortBy } from 'projects/varda-shared/src/lib/models/koodisto-models';
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

@Component({
  selector: 'app-varda-toimipaikka-form',
  templateUrl: './varda-toimipaikka-form.component.html',
  styleUrls: ['./varda-toimipaikka-form.component.css']
})
export class VardaToimipaikkaFormComponent extends VardaFormAccordionAbstractComponent implements OnInit, OnDestroy {
  @ViewChild('formContent') formContent: ElementRef;
  @Input() toimipaikka: VardaToimipaikkaMinimalDto;
  @Output() saveToimipaikkaFormSuccess = new EventEmitter<VardaToimipaikkaDTO>(true);
  @Output() valuesChanged = new EventEmitter<boolean>(true);

  koodistoEnum = KoodistoEnum;
  toimijaAccess: UserAccess;
  tallentajaAccess: boolean;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  showFormContinuesWarning: boolean;
  formGroup: FormGroup;
  toimipaikkaFormErrors: Observable<Array<ErrorTree>>;
  isSubmitting = false;
  minEndDate: Date;
  maxEndDate: Date;
  toimintamuotoOptions$: Observable<KoodistoDTO>;
  kuntaOptions$: Observable<KoodistoDTO>;
  jarjestamismuotoOptions$: Observable<KoodistoDTO>;
  kielikoodisto: Array<CodeDTO>;
  kasvatusopillinenOptions$: Observable<KoodistoDTO>;
  postitoimipaikkaOptions$: Observable<KoodistoDTO>;
  filteredKayntiosoitePostitoimipaikat: Array<CodeDTO> = [];
  filteredPostitoimipaikat: Array<CodeDTO> = [];
  postiosoiteToggleBoolean = false;
  toimipaikkaKooste: ToimipaikkaKooste;

  private errorService: VardaErrorMessageService;
  private subscriptions: Array<Subscription> = [];
  private formGroupSubscriptions: Array<Subscription> = [];

  constructor(
    private authService: AuthService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private snackBarService: VardaSnackBarService,
    private koodistoService: VardaKoodistoService,
    private translateService: TranslateService,
    private koosteService: VardaKoosteApiService,
    modalService: VardaModalService,
  ) {
    super(modalService);
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.toimijaAccess = this.authService.getUserAccess();
    this.toimipaikkaFormErrors = this.errorService.initErrorList();
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();

    this.toimintamuotoOptions$ = this.koodistoService.getKoodisto(KoodistoEnum.toimintamuoto, KoodistoSortBy.codeValue);
    this.kuntaOptions$ = this.koodistoService.getKoodisto(KoodistoEnum.kunta, KoodistoSortBy.codeValue);
    this.kasvatusopillinenOptions$ = this.koodistoService.getKoodisto(KoodistoEnum.kasvatusopillinenjarjestelma, KoodistoSortBy.codeValue);
    this.postitoimipaikkaOptions$ = this.koodistoService.getKoodisto(KoodistoEnum.posti, KoodistoSortBy.codeValue);

    // Depending on if current Vakajarjestaja is kunnallinen or yksityinen, exclude jarjestamismuoto options
    const excludeJarjestamismuotoCodes = this.vakajarjestajaService.getSelectedVakajarjestaja().kunnallinen_kytkin ? ['jm04', 'jm05'] : ['jm01'];
    this.jarjestamismuotoOptions$ = this.koodistoService.getKoodisto(KoodistoEnum.jarjestamismuoto, KoodistoSortBy.codeValue)
      .pipe(map(koodisto => {
        koodisto.codes = koodisto.codes.filter(code => !excludeJarjestamismuotoCodes.includes(code.code_value.toLowerCase()));
        return koodisto;
      }));
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

    this.subscriptions.push(
      this.vakajarjestajaApiService.listenToimipaikkaListUpdate().subscribe(() =>
        this.vakajarjestajaApiService.initFormErrorList(this.selectedVakajarjestaja.id, this.toimipaikka)),
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
    this.isEdit = false;
    this.formGroup.disable();
    this.valuesChanged.emit(false);
  }

  enableForm() {
    this.isEdit = true;
    this.formGroup.enable();
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting = false, 500);
  }

  initForm() {
    this.formGroupSubscriptions.forEach(subscription => subscription.unsubscribe());
    this.formGroup = new FormGroup({
      lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
      id: new FormControl(this.toimipaikkaKooste?.id),
      nimi: new FormControl(this.toimipaikkaKooste?.nimi,
        [Validators.required, Validators.minLength(3), Validators.maxLength(200), VardaFormValidators.hasCharacters(), VardaFormValidators.rejectSpecialChars]),
      organisaatio_oid: new FormControl(this.toimipaikkaKooste?.organisaatio_oid),
      kayntiosoite: new FormControl(this.toimipaikkaKooste?.kayntiosoite,
        [Validators.required, Validators.minLength(3), Validators.maxLength(100), VardaFormValidators.hasCharacters(), VardaFormValidators.rejectSpecialChars]),
      kayntiosoite_postinumero: new FormControl(this.toimipaikkaKooste?.kayntiosoite_postinumero, [Validators.required]),
      kayntiosoite_postitoimipaikka: new FormControl(this.toimipaikkaKooste?.kayntiosoite_postitoimipaikka, [Validators.required]),
      postiosoite: new FormControl(this.toimipaikkaKooste?.postiosoite,
        [Validators.required, Validators.minLength(3), Validators.maxLength(100), VardaFormValidators.hasCharacters(), VardaFormValidators.rejectSpecialChars]),
      postinumero: new FormControl(this.toimipaikkaKooste?.postinumero, [Validators.required]),
      postitoimipaikka: new FormControl(this.toimipaikkaKooste?.postitoimipaikka, [Validators.required]),
      kunta_koodi: new FormControl(this.toimipaikkaKooste?.kunta_koodi.toLocaleUpperCase(), [Validators.required]),
      puhelinnumero: new FormControl(this.toimipaikkaKooste?.puhelinnumero, [Validators.required, VardaFormValidators.validStringFormat.bind(null, { regex: '^(\\+358)[1-9]\\d{5,10}$' })]),
      sahkopostiosoite: new FormControl(this.toimipaikkaKooste?.sahkopostiosoite, [Validators.required, VardaFormValidators.validStringFormat.bind(null, { regex: '^[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+(\\.[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+)*@[A-Za-z0-9][A-Za-z0-9-]+(\\.[A-Za-z0-9-]+)*(\\.[A-Za-z]{2,})$' })]),
      toimintamuoto_koodi: new FormControl(this.toimipaikkaKooste?.toimintamuoto_koodi.toLocaleUpperCase(), [Validators.required]),
      jarjestamismuoto_koodi: new FormControl(this.toimipaikkaKooste?.jarjestamismuoto_koodi.map(koodi => koodi.toLocaleUpperCase()), [Validators.required]),
      asiointikieli_koodi: new FormControl(this.toimipaikkaKooste?.asiointikieli_koodi.map(koodi => koodi.toLocaleUpperCase()), [Validators.required]),
      kasvatusopillinen_jarjestelma_koodi: new FormControl(this.toimipaikkaKooste?.kasvatusopillinen_jarjestelma_koodi.toLocaleUpperCase() || 'KJ98', [Validators.required]),
      varhaiskasvatuspaikat: new FormControl(this.toimipaikkaKooste?.varhaiskasvatuspaikat, [Validators.required, Validators.min(0)]),
      alkamis_pvm: new FormControl(this.toimipaikkaKooste ? moment(this.toimipaikkaKooste?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.toimipaikkaKooste?.paattymis_pvm ? moment(this.toimipaikkaKooste?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
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

    this.checkFormErrors(this.vakajarjestajaApiService, 'toimipaikka', this.toimipaikka?.id);
  }

  getToimipaikkaKooste() {
    this.subscriptions.push(
      this.koosteService.getToimipaikkaKooste(this.toimipaikka?.id).subscribe({
        next: result => {
          this.toimipaikkaKooste = result;
          this.vakajarjestajaApiService.activeToimipaikka.next(this.toimipaikkaKooste);
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
        ...form.value,
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
            this.toimipaikkaKooste = {...result, vakajarjestaja_id: this.selectedVakajarjestaja.id,
              vakajarjestaja_nimi: this.selectedVakajarjestaja.nimi,
              kielipainotukset: activeToimipaikka?.kielipainotukset || [],
              toiminnalliset_painotukset: activeToimipaikka?.toiminnalliset_painotukset || []};
            this.initForm();
            this.vakajarjestajaApiService.activeToimipaikka.next(this.toimipaikkaKooste);
          },
          error: err => this.errorService.handleError(err, this.snackBarService)
        })
      );
    } else {
      this.disableSubmit();
    }
  }

  changePostinumero(postinumero: string, kayntiosoite?: boolean) {
    this.postitoimipaikkaOptions$.pipe(take(1)).subscribe(postitoimipaikkaOptions => {
      if (!postinumero) {
        return;
      }

      const filteredPostitoimipaikat = postinumero.length > 1 ? postitoimipaikkaOptions.codes.filter(toimipaikka => toimipaikka.code_value.startsWith(postinumero)) : [];
      const postitoimipaikka = filteredPostitoimipaikat.find(toimipaikka => toimipaikka.code_value === postinumero);

      const kayntiosoiteCtrl = this.formGroup.get('kayntiosoite_postitoimipaikka');
      const postitoimipaikkaCtrl = this.formGroup.get('postitoimipaikka');

      if (kayntiosoite) {
        if (postinumero.length === 5 && !postitoimipaikka) {
          const postinumeroCtrl = this.formGroup.get('kayntiosoite_postinumero');
          postinumeroCtrl.setValue(postinumero.substr(0, 4));
          postinumeroCtrl.markAsTouched();
        }
        kayntiosoiteCtrl.setValue(postitoimipaikka?.name);
        kayntiosoiteCtrl.markAsTouched();
        this.filteredKayntiosoitePostitoimipaikat = postitoimipaikka ? [] : filteredPostitoimipaikat;
      } else {
        if (postinumero.length === 5 && !postitoimipaikka) {
          const postinumeroCtrl = this.formGroup.get('postinumero');
          postinumeroCtrl.setValue(postinumero.substr(0, 4));
          postinumeroCtrl.markAsTouched();
        }
        postitoimipaikkaCtrl.setValue(postitoimipaikka?.name);
        postitoimipaikkaCtrl.markAsTouched();
        this.filteredPostitoimipaikat = postitoimipaikka ? [] : filteredPostitoimipaikat;
      }
    });
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
  }

  togglePostinumero(change: MatCheckboxChange) {
    this.postiosoiteToggleBoolean = change.checked;

    if (this.postiosoiteToggleBoolean) {
      this.formGroup.get('postiosoite').setValue(this.formGroup.get('kayntiosoite').value);
      this.formGroup.get('postinumero').setValue(this.formGroup.get('kayntiosoite_postinumero').value);
      this.formGroup.updateValueAndValidity();
    }
  }

  startDateChange(startDate: Moment) {
    this.minEndDate = startDate?.clone().add(1, 'days').toDate();
    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  endDateChange(endDate: Moment) {
    this.maxEndDate = endDate?.clone().toDate();
  }

  ngOnDestroy() {
    this.vakajarjestajaApiService.activeToimipaikka.next(null);
    this.subscriptions.forEach(sub => sub.unsubscribe());
    this.formGroupSubscriptions.forEach(sub => sub.unsubscribe());
  }
}
