import { Component, ElementRef, EventEmitter, Input, OnDestroy, OnInit, Output, ViewChild } from '@angular/core';
import { AbstractControl, FormControl, FormGroup, Validators } from '@angular/forms';
import { MatCheckboxChange } from '@angular/material/checkbox';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { Moment } from 'moment';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { BehaviorSubject, fromEvent, Observable, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, filter, mergeMap, take } from 'rxjs/operators';
import { CodeDTO, KoodistoDTO, KoodistoEnum, KoodistoSortBy, VardaKoodistoService } from 'varda-shared';
import { AuthService } from '../../../core/auth/auth.service';
import { ErrorTree, VardaErrorMessageService } from '../../../core/services/varda-error-message.service';
import { VardaSnackBarService } from '../../../core/services/varda-snackbar.service';
import { VardaVakajarjestajaApiService } from '../../../core/services/varda-vakajarjestaja-api.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaFormValidators } from '../../../shared/validators/varda-form-validators';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { VardaToimipaikkaDTO, VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { Hallinnointijarjestelma, Lahdejarjestelma } from '../../../utilities/models/enums/hallinnointijarjestelma';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { VardaDateService } from '../../services/varda-date.service';

@Component({
  selector: 'app-varda-toimipaikka-form',
  templateUrl: './varda-toimipaikka-form.component.html',
  styleUrls: ['./varda-toimipaikka-form.component.css']
})
export class VardaToimipaikkaFormComponent implements OnInit, OnDestroy {
  @Input() toimipaikka: VardaToimipaikkaDTO;
  @Output() saveToimipaikkaFormSuccess = new EventEmitter<VardaToimipaikkaDTO>(true);
  @Output() valuesChanged = new EventEmitter<boolean>(true);
  @ViewChild('formContent') formContent: ElementRef;
  private errorService: VardaErrorMessageService;
  i18n = VirkailijaTranslations;
  koodistoEnum = KoodistoEnum;
  toimijaAccess: UserAccess;
  tallentajaAccess: boolean;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  showFormContinuesWarning: boolean;
  toimipaikkaForm: FormGroup;
  toimipaikkaFormErrors: Observable<Array<ErrorTree>>;
  subscriptions: Array<Subscription> = [];
  isSubmitting = new BehaviorSubject<boolean>(false);
  isEdit = false;
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

  constructor(
    private authService: AuthService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private snackBarService: VardaSnackBarService,
    private koodistoService: VardaKoodistoService,
    private translateService: TranslateService,
  ) {
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.toimijaAccess = this.authService.getUserAccess();
    this.tallentajaAccess = true;
    this.toimipaikkaFormErrors = this.errorService.initErrorList();
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    this.toimintamuotoOptions$ = this.koodistoService.getKoodisto(KoodistoEnum.toimintamuoto, KoodistoSortBy.codeValue);
    this.kuntaOptions$ = this.koodistoService.getKoodisto(KoodistoEnum.kunta, KoodistoSortBy.codeValue);
    this.jarjestamismuotoOptions$ = this.koodistoService.getKoodisto(KoodistoEnum.jarjestamismuoto, KoodistoSortBy.codeValue);
    this.kasvatusopillinenOptions$ = this.koodistoService.getKoodisto(KoodistoEnum.kasvatusopillinenjarjestelma, KoodistoSortBy.codeValue);
    this.postitoimipaikkaOptions$ = this.koodistoService.getKoodisto(KoodistoEnum.posti, KoodistoSortBy.codeValue);



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

        return a.name.localeCompare(b.name);
      });
    });
  }

  ngOnInit() {
    this.tallentajaAccess = this.toimijaAccess.lapsitiedot.tallentaja;
    if (this.toimipaikka) {
      if (this.toimipaikka.paos_organisaatio_url || this.toimipaikka.hallinnointijarjestelma !== Hallinnointijarjestelma.VARDA) {
        this.tallentajaAccess = false;
      }

      this.getToimipaikka(this.toimipaikka.id);
    } else {
      this.initForm();
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  bindScrollHandlers(): void {
    fromEvent(this.formContent.nativeElement, 'scroll')
      .pipe(debounceTime(300))
      .subscribe((e: any) => {
        const ct = e.target;
        this.showFormContinuesWarning = ct.scrollHeight - ct.clientHeight - ct.scrollTop > 200;
      });
  }

  disableForm() {
    this.isEdit = false;
    this.toimipaikkaForm.disable();
    this.valuesChanged.emit(false);
  }

  enableForm() {
    this.isEdit = true;
    this.toimipaikkaForm.enable();
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting.next(false), 500);
  }

  initForm(toimipaikka?: VardaToimipaikkaDTO) {
    this.toimipaikka = toimipaikka;
    this.toimipaikkaForm = new FormGroup({
      lahdejarjestelma: new FormControl(this.toimipaikka?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      id: new FormControl(toimipaikka?.id),
      nimi: new FormControl(toimipaikka?.nimi,
        [Validators.required, Validators.minLength(3), Validators.maxLength(200), VardaFormValidators.hasCharacters(), VardaFormValidators.rejectSpecialChars]),
      organisaatio_oid: new FormControl(toimipaikka?.organisaatio_oid || this.selectedVakajarjestaja.organisaatio_oid, [Validators.required]),
      kayntiosoite: new FormControl(toimipaikka?.kayntiosoite,
        [Validators.required, Validators.minLength(3), Validators.maxLength(100), VardaFormValidators.hasCharacters(), VardaFormValidators.rejectSpecialChars]),
      kayntiosoite_postinumero: new FormControl(toimipaikka?.kayntiosoite_postinumero, [Validators.required]),
      kayntiosoite_postitoimipaikka: new FormControl(toimipaikka?.kayntiosoite_postitoimipaikka, [Validators.required]),
      postiosoite: new FormControl(toimipaikka?.postiosoite,
        [Validators.required, Validators.minLength(3), Validators.maxLength(100), VardaFormValidators.hasCharacters(), VardaFormValidators.rejectSpecialChars]),
      postinumero: new FormControl(toimipaikka?.postinumero, [Validators.required]),
      postitoimipaikka: new FormControl(toimipaikka?.postitoimipaikka, [Validators.required]),
      kunta_koodi: new FormControl(toimipaikka?.kunta_koodi.toLocaleUpperCase(), [Validators.required]),
      puhelinnumero: new FormControl(toimipaikka?.puhelinnumero, [Validators.required, VardaFormValidators.validStringFormat.bind(null, { regex: '^(\\+358)[1-9]\\d{5,10}$' })]),
      sahkopostiosoite: new FormControl(toimipaikka?.sahkopostiosoite, [Validators.required, VardaFormValidators.validStringFormat.bind(null, { regex: '^[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+(\\.[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+)*@[A-Za-z0-9][A-Za-z0-9-]+(\\.[A-Za-z0-9-]+)*(\\.[A-Za-z]{2,})$' })]),
      toimintamuoto_koodi: new FormControl(toimipaikka?.toimintamuoto_koodi.toLocaleUpperCase(), [Validators.required]),
      jarjestamismuoto_koodi: new FormControl(toimipaikka?.jarjestamismuoto_koodi.map(koodi => koodi.toLocaleUpperCase()), [Validators.required]),
      asiointikieli_koodi: new FormControl(toimipaikka?.asiointikieli_koodi.map(koodi => koodi.toLocaleUpperCase()), [Validators.required]),
      kasvatusopillinen_jarjestelma_koodi: new FormControl(toimipaikka?.kasvatusopillinen_jarjestelma_koodi.toLocaleUpperCase() || 'KJ98', [Validators.required]),
      varhaiskasvatuspaikat: new FormControl(toimipaikka?.varhaiskasvatuspaikat, [Validators.required, Validators.min(0)]),
      alkamis_pvm: new FormControl(toimipaikka ? moment(toimipaikka?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(toimipaikka?.paattymis_pvm ? moment(toimipaikka?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
      vakajarjestaja: new FormControl(toimipaikka?.vakajarjestaja || this.selectedVakajarjestaja.url)
    });


    if (!this.tallentajaAccess || this.toimipaikka) {
      this.disableForm();
      if (this.toimipaikka) {
        this.checkPostiosoiteToggle();
        this.startDateChange(this.toimipaikkaForm.get('alkamis_pvm')?.value);
        this.endDateChange(this.toimipaikkaForm.get('paattymis_pvm')?.value);
      }
    } else {
      this.enableForm();
    }

    this.subscriptions.push(
      this.toimipaikkaForm.statusChanges
        .pipe(filter(() => !this.toimipaikkaForm.pristine), distinctUntilChanged())
        .subscribe(() => this.valuesChanged.emit(true)),
      this.toimipaikkaForm.get('kayntiosoite_postinumero').valueChanges.subscribe(postinumero =>
        this.changePostinumero(postinumero, true)
      ),
      this.toimipaikkaForm.get('postinumero').valueChanges.subscribe(postinumero =>
        this.changePostinumero(postinumero)
      ),
    );
  }

  getToimipaikka(toimipaikka_id: number) {
    this.vakajarjestajaApiService.getToimipaikka(toimipaikka_id).subscribe({
      next: toimipaikkaData => this.initForm(toimipaikkaData),
      error: err => this.errorService.handleError(err, this.snackBarService)
    });
  }

  saveToimipaikka(form: FormGroup) {
    this.isSubmitting.next(true);
    form.markAllAsTouched();
    this.errorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const toimipaikkaDTO: VardaToimipaikkaDTO = {
        ...form.value,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      const updateToimipaikka = this.toimipaikka ? this.vakajarjestajaApiService.updateToimipaikka(toimipaikkaDTO) : this.vakajarjestajaApiService.createToimipaikka(toimipaikkaDTO);

      updateToimipaikka.subscribe({
        next: toimipaikkaData => {
          this.snackBarService.success(this.i18n.toimipaikka_save_success);
          this.saveToimipaikkaFormSuccess.emit(toimipaikkaData);

          this.disableForm();
          this.getToimipaikka(toimipaikkaData.id);
        },
        error: err => this.errorService.handleError(err, this.snackBarService)
      }).add(() => this.disableSubmit());
    } else {
      this.disableSubmit();
    }
  }

  changePostinumero(postinumero: string, kayntiosoite?: boolean) {
    this.postitoimipaikkaOptions$.pipe(take(1)).subscribe(postitoimipaikkaOptions => {
      const filteredPostitoimipaikat = postinumero.length > 1 ? postitoimipaikkaOptions.codes.filter(toimipaikka => toimipaikka.code_value.startsWith(postinumero)) : [];
      const postitoimipaikka = filteredPostitoimipaikat.find(toimipaikka => toimipaikka.code_value === postinumero);

      const kayntiosoiteCtrl = this.toimipaikkaForm.get('kayntiosoite_postitoimipaikka');
      const postitoimipaikkaCtrl = this.toimipaikkaForm.get('postitoimipaikka');

      if (kayntiosoite) {
        if (postinumero.length === 5 && !postitoimipaikka) {
          const postinumeroCtrl = this.toimipaikkaForm.get('kayntiosoite_postinumero');
          postinumeroCtrl.setValue(postinumero.substr(0, 4));
          postinumeroCtrl.markAsTouched();
        }
        kayntiosoiteCtrl.setValue(postitoimipaikka?.name);
        kayntiosoiteCtrl.markAsTouched();
        this.filteredKayntiosoitePostitoimipaikat = postitoimipaikka ? [] : filteredPostitoimipaikat;
      } else {
        if (postinumero.length === 5 && !postitoimipaikka) {
          const postinumeroCtrl = this.toimipaikkaForm.get('postinumero');
          postinumeroCtrl.setValue(postinumero.substr(0, 4));
          postinumeroCtrl.markAsTouched();
        }
        postitoimipaikkaCtrl.setValue(postitoimipaikka?.name);
        postitoimipaikkaCtrl.markAsTouched();
        this.filteredPostitoimipaikat = postitoimipaikka ? [] : filteredPostitoimipaikat;
      }
    });
  }


  changePostitoimipaikka(postinumero: string, toimipaikkaControl: AbstractControl) {
    this.postitoimipaikkaOptions$.pipe(take(1)).subscribe(postitoimipaikat => {
      const pt = postitoimipaikat.codes.find(koodi => koodi.code_value === postinumero)?.name;
      toimipaikkaControl.setValue(postitoimipaikat.codes.find(koodi => koodi.code_value === postinumero)?.name);
      toimipaikkaControl.markAsTouched();
    });
  }

  checkPostiosoiteToggle() {
    const kayntiosoite = this.toimipaikkaForm.get('kayntiosoite')?.value;
    const kayntiosoitePostinumero = this.toimipaikkaForm.get('kayntiosoite_postinumero')?.value;
    const kayntiosoitePostitoimipaikka = this.toimipaikkaForm.get('kayntiosoite_postitoimipaikka')?.value;
    const postiosoite = this.toimipaikkaForm.get('postiosoite')?.value;
    const postitoimipaikka = this.toimipaikkaForm.get('postitoimipaikka')?.value;
    const postinumero = this.toimipaikkaForm.get('postinumero')?.value;

    if (kayntiosoite && postiosoite && kayntiosoitePostitoimipaikka && postitoimipaikka && kayntiosoitePostinumero && postinumero) {
      this.postiosoiteToggleBoolean = kayntiosoite === postiosoite && kayntiosoitePostitoimipaikka === postitoimipaikka && kayntiosoitePostinumero === postinumero;
    } else {
      this.postiosoiteToggleBoolean = false;
    }
  }

  togglePostinumero(change: MatCheckboxChange) {
    this.postiosoiteToggleBoolean = change.checked;

    if (this.postiosoiteToggleBoolean) {
      this.toimipaikkaForm.get('postiosoite').setValue(this.toimipaikkaForm.get('kayntiosoite').value);
      this.toimipaikkaForm.get('postinumero').setValue(this.toimipaikkaForm.get('kayntiosoite_postinumero').value);
      this.toimipaikkaForm.updateValueAndValidity();
    }
  }

  startDateChange(startDate: Moment) {
    this.minEndDate = startDate?.clone().add(1, 'days').toDate();
    setTimeout(() => this.toimipaikkaForm.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  endDateChange(endDate: Moment) {
    this.maxEndDate = endDate?.clone().toDate();
  }

}

