import { Component, OnInit, Input, ViewChild, ElementRef, OnDestroy, EventEmitter, Output } from '@angular/core';
import { TyontekijaListDTO } from '../../../utilities/models/dto/varda-tyontekija-dto.model';
import { LapsiListDTO } from '../../../utilities/models/dto/varda-lapsi-dto.model';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { HenkilostoErrorMessageService, ErrorTree } from '../../../core/services/varda-henkilosto-error-message.service';
import { VardaApiService } from '../../../core/services/varda-api.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { fromEvent, Observable, Subscription, BehaviorSubject } from 'rxjs';
import { debounceTime, distinctUntilChanged, filter } from 'rxjs/operators';
import { VardaHenkiloDTO } from '../../../utilities/models';
import { HenkiloRooliEnum } from '../../../utilities/models/enums/henkilorooli.enum';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { VardaFormValidators } from '../../../shared/validators/varda-form-validators';
import { Lahdejarjestelma } from '../../../utilities/models/enums/hallinnointijarjestelma';
import { MatRadioChange } from '@angular/material/radio';
import { VardaSnackBarService } from '../../../core/services/varda-snackbar.service';

@Component({
  selector: 'app-varda-henkilo-form',
  templateUrl: './varda-henkilo-form.component.html',
  styleUrls: ['./varda-henkilo-form.component.css']
})
export class VardaHenkiloFormComponent implements OnInit, OnDestroy {
  @Input() henkilonSuhde: TyontekijaListDTO | LapsiListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Output() valuesChanged = new EventEmitter<boolean>(true);
  @Output() closeHenkiloForm = new EventEmitter(true);
  @ViewChild('formContent', { static: true }) formContent: ElementRef;

  i18n = VirkailijaTranslations;
  HenkiloRooliEnum = HenkiloRooliEnum;
  currentHenkilo: VardaHenkiloDTO;
  formContinuesBoolean: boolean;
  henkiloForm: FormGroup;
  henkiloFormErrors: Observable<Array<ErrorTree>>;
  subscriptions: Array<Subscription> = [];
  isLoading = new BehaviorSubject<boolean>(false);

  constructor(
    private henkilostoErrorService: HenkilostoErrorMessageService,
    private vardaApiService: VardaApiService,
    private snackBarService: VardaSnackBarService,
  ) {
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  ngOnInit() {
    this.bindScrollHandlers();

    this.henkilostoErrorService.resetErrorList();
    this.henkiloFormErrors = this.henkilostoErrorService.initErrorList();

    if (this.henkilonSuhde?.henkilo_id) {
      this.getHenkilo(this.henkilonSuhde.henkilo_id);
    } else {
      this.henkiloForm = new FormGroup({
        addWithSsnOrOid: new FormControl(true),
        henkilotunnus: new FormControl(null, [Validators.required, VardaFormValidators.validSSN]),
        henkilo_oid: new FormControl(null, [Validators.required, VardaFormValidators.validOppijanumero]),
        lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
        etunimet: new FormControl(null, [Validators.required, VardaFormValidators.validHenkiloName]),
        kutsumanimi: new FormControl(null, [Validators.required, VardaFormValidators.validHenkiloName]),
        sukunimi: new FormControl(null, [Validators.required, VardaFormValidators.validHenkiloName])
      }, VardaFormValidators.nicknamePartOfFirstname);

      this.henkiloForm.controls.henkilo_oid.disable();

      this.subscriptions.push(
        this.henkiloForm.statusChanges
          .pipe(filter(() => this.henkiloForm.dirty), distinctUntilChanged())
          .subscribe(() => this.formValuesChanged(true)),
        this.henkiloForm.get('etunimet').valueChanges.subscribe(() => this.henkiloForm.get('kutsumanimi').updateValueAndValidity())
      );
    }
  }

  getHenkilo(henkiloId: number): void {
    this.vardaApiService.getHenkilo(henkiloId).subscribe({
      next: henkilo => this.currentHenkilo = henkilo,
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  bindScrollHandlers(): void {
    fromEvent(this.formContent.nativeElement, 'scroll')
      .pipe(debounceTime(300))
      .subscribe((e: any) => {
        const ct = e.target;
        this.formContinuesBoolean = ct.scrollHeight - ct.clientHeight - ct.scrollTop > 200;
      });
  }

  addWithSsnOrOidChanged(radioEvent: MatRadioChange): void {
    if (radioEvent.value) {
      this.henkiloForm.controls.henkilotunnus.enable();
      this.henkiloForm.controls.henkilo_oid.disable();
    } else {
      this.henkiloForm.controls.henkilotunnus.disable();
      this.henkiloForm.controls.henkilo_oid.enable();
    }
  }

  saveHenkilo(henkiloForm: FormGroup) {
    henkiloForm.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (HenkilostoErrorMessageService.formIsValid(henkiloForm)) {
      this.isLoading.next(true);

      this.vardaApiService.createHenkilo(henkiloForm.value).subscribe({
        next: henkiloData => {
          this.currentHenkilo = henkiloData;
        },
        error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
      }).add(() => setTimeout(() => this.isLoading.next(false), 2000));
    }
  }

  formValuesChanged(hasChanged: boolean) {
    this.valuesChanged.emit(hasChanged);
  }

  closeForm() {
    this.closeHenkiloForm.emit();
  }
}
