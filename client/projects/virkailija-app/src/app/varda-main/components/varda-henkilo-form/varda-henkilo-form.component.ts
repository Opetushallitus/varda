import { Component, OnInit, OnChanges, Input, ViewChild, ElementRef, OnDestroy, EventEmitter, Output } from '@angular/core';
import { TyontekijaListDTO } from '../../../utilities/models/dto/varda-tyontekija-dto.model';
import { LapsiListDTO } from '../../../utilities/models/dto/varda-lapsi-dto.model';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { HenkilostoErrorMessageService, ErrorTree } from '../../../core/services/varda-henkilosto-error-message.service';
import { VardaApiService } from '../../../core/services/varda-api.service';
import { VardaApiWrapperService } from '../../../core/services/varda-api-wrapper.service';
import { VardaModalService } from '../../../core/services/varda-modal.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaErrorMessageService } from '../../../core/services/varda-error-message.service';
import { TranslateService } from '@ngx-translate/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { fromEvent, Observable, Subscription, BehaviorSubject } from 'rxjs';
import { debounceTime, distinctUntilChanged, filter } from 'rxjs/operators';
import { VardaHenkiloDTO } from '../../../utilities/models';
import { HenkiloRooliEnum } from '../../../utilities/models/enums/henkilorooli.enum';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { VardaFormValidators } from '../../../shared/validators/varda-form-validators';
import { Lahdejarjestelma } from '../../../utilities/models/enums/hallinnointijarjestelma';
import { MatRadioChange } from '@angular/material/radio';

declare var $: any;

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
    private vardaModalService: VardaModalService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vardaErrorMessageService: VardaErrorMessageService,
    private translateService: TranslateService,
    private modalService: VardaModalService
  ) {
    // TODO: poista lapsiform reworkissa
    this.vardaModalService.modalOpenObs('lapsiSuccessModal').subscribe((isOpen: boolean) => {
      if (isOpen) {
        $(`#lapsiSuccessModal`).modal({ keyboard: true, focus: true });
        setTimeout(() => {
          $(`#lapsiSuccessModal`).modal('hide');
        }, 2500);
      }
    });
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
      error: err => this.henkilostoErrorService.handleError(err)
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

  onSaveLapsiSuccess(err?: any) {
    if (err) {
      this.henkilostoErrorService.handleError(err);
    } else {
      this.closeForm();
      this.vardaModalService.openModal('lapsiSuccessModal', true);
    }
  }

  closeForm() {
    this.closeHenkiloForm.emit();
  }

  saveHenkilo(henkiloForm: FormGroup) {
    henkiloForm.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (HenkilostoErrorMessageService.formIsValid(henkiloForm)) {
      this.isLoading.next(true);

      this.vardaApiService.createHenkilo(henkiloForm.value).subscribe({
        next: henkiloData => {
          console.log(henkiloData);
          this.currentHenkilo = henkiloData;
        },
        error: err => this.henkilostoErrorService.handleError(err)
      }).add(() => setTimeout(() => this.isLoading.next(false), 2000));
    }
  }

  formValuesChanged(hasChanged: boolean) {
    this.valuesChanged.emit(hasChanged);
  }

}
