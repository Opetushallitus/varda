import { Component, OnInit, Input, Output, EventEmitter, ElementRef, OnDestroy } from '@angular/core';
import { FormGroup, FormControl, Validators, AbstractControl, ValidatorFn } from '@angular/forms';
import * as moment from 'moment';
import { Moment } from 'moment';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { finalize, Observable, Subscription } from 'rxjs';
import { filter, distinctUntilChanged } from 'rxjs/operators';
import { VardaKoodistoService, VardaDateService } from 'varda-shared';
import { KoodistoEnum, CodeDTO } from 'projects/varda-shared/src/lib/models/koodisto-models';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import {
  LapsiKoosteVakapaatos, LapsiKoosteVakasuhde
} from '../../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { sortByAlkamisPvm } from '../../../../../../utilities/helper-functions';
import { VardaVarhaiskasvatuspaatosDTO } from '../../../../../../utilities/models/dto/varda-lapsi-dto.model';


interface JarjestamismuodotCode extends CodeDTO {
  disabled?: boolean;
}

export const kunnallisetJarjestamismuodot = ['JM01', 'JM02', 'JM03'];

@Component({
  selector: 'app-varda-varhaiskasvatuspaatos',
  templateUrl: './varda-varhaiskasvatuspaatos.component.html',
  styleUrls: [
    './varda-varhaiskasvatuspaatos.component.css',
    '../varda-varhaiskasvatuspaatokset.component.css',
    '../../varda-lapsi-form.component.css',
    '../../../varda-henkilo-form.component.css'
  ]
})
export class VardaVarhaiskasvatuspaatosComponent extends VardaFormAccordionAbstractComponent implements OnInit, OnDestroy {
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() lapsitiedotTallentaja: boolean;
  @Input() varhaiskasvatuspaatos: LapsiKoosteVakapaatos;
  @Output() addObject = new EventEmitter<LapsiKoosteVakapaatos>(true);
  @Output() deleteObject = new EventEmitter<number>(true);

  koodistoEnum = KoodistoEnum;
  element: ElementRef;
  addVarhaiskasvatussuhdeBoolean: boolean;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  isSubmitting = false;
  varhaiskasvatuspaatosFormErrors: Observable<Array<ErrorTree>>;
  jarjestamismuotoKoodisto: Array<JarjestamismuodotCode>;
  tilapainenVarhaiskasvatusBoolean: boolean;
  minStartDate: Date;
  minEndDate: Date;
  varhaiskasvatussuhdeList: Array<LapsiKoosteVakasuhde> = [];
  lapsiId: number;
  isPaos: boolean;

  private errorMessageService: VardaErrorMessageService;
  private tilapainenValidator = ((): ValidatorFn => (control: AbstractControl) => control.value ? null : {tilapainen: true})();
  private subscriptions: Array<Subscription> = [];

  constructor(
    private el: ElementRef,
    private lapsiService: VardaLapsiService,
    private koodistoService: VardaKoodistoService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private snackBarService: VardaSnackBarService,
    private translateService: TranslateService,
    modalService: VardaModalService
  ) {
    super(modalService);
    this.element = this.el;
    this.errorMessageService = new VardaErrorMessageService(translateService);
    this.varhaiskasvatuspaatosFormErrors = this.errorMessageService.initErrorList();
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();

    const activeLapsi = this.lapsiService.activeLapsi.getValue();
    this.lapsiId = activeLapsi.id;
    this.isPaos = !!activeLapsi.paos_organisaatio_oid;
  }

  ngOnInit() {
    this.formGroup = new FormGroup({
      id: new FormControl(this.varhaiskasvatuspaatos?.id),
      lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
      lapsi: new FormControl(this.lapsiService.getLapsiUrl(this.lapsiId)),
      toimipaikka_oid: new FormControl(this.varhaiskasvatuspaatos ? null : this.henkilonToimipaikka?.organisaatio_oid),
      hakemus_pvm: new FormControl(this.varhaiskasvatuspaatos ? moment(this.varhaiskasvatuspaatos?.hakemus_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      alkamis_pvm: new FormControl(this.varhaiskasvatuspaatos ? moment(this.varhaiskasvatuspaatos?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.varhaiskasvatuspaatos?.paattymis_pvm ? moment(this.varhaiskasvatuspaatos?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
      jarjestamismuoto_koodi: new FormControl(this.varhaiskasvatuspaatos?.jarjestamismuoto_koodi.toLocaleUpperCase(), Validators.required),
      vuorohoito_kytkin: new FormControl(this.varhaiskasvatuspaatos?.vuorohoito_kytkin, Validators.required),
      paivittainen_vaka_kytkin: new FormControl(this.varhaiskasvatuspaatos?.paivittainen_vaka_kytkin, Validators.required),
      kokopaivainen_vaka_kytkin: new FormControl(this.varhaiskasvatuspaatos?.kokopaivainen_vaka_kytkin, Validators.required),
      tilapainen_vaka_kytkin: new FormControl(this.varhaiskasvatuspaatos?.tilapainen_vaka_kytkin, Validators.required),
      tuntimaara_viikossa: new FormControl(this.varhaiskasvatuspaatos?.tuntimaara_viikossa, [Validators.pattern('^\\d+([,.]\\d{1})?$'), Validators.min(1), Validators.max(120), Validators.required]),
    });

    if (this.varhaiskasvatuspaatos) {
      this.varhaiskasvatussuhdeList = this.varhaiskasvatuspaatos.varhaiskasvatussuhteet.sort(sortByAlkamisPvm);
      this.disableForm();
      this.changeJarjestamismuoto(this.varhaiskasvatuspaatos.jarjestamismuoto_koodi);
      this.checkFormErrors(this.lapsiService, 'varhaiskasvatuspaatos', this.varhaiskasvatuspaatos?.id);
    } else {
      this.enableForm();
      this.togglePanel(true);
    }

    this.initDateFilters();

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true)),
      this.formGroup.get('tilapainen_vaka_kytkin').valueChanges
        .subscribe((value: boolean) => this.tilapainenVakaChange(value)),
      this.koodistoService.getKoodisto(KoodistoEnum.jarjestamismuoto).subscribe(koodisto =>
        this.handleJarjestamismuodot(koodisto.codes))
    );
  }

  saveVarhaiskasvatuspaatos(form: FormGroup): void {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.errorMessageService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const varhaiskasvatuspaatosDTO: VardaVarhaiskasvatuspaatosDTO = {
        ...form.value,
        hakemus_pvm: form.value.hakemus_pvm.format(VardaDateService.vardaApiDateFormat),
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      const observable = this.varhaiskasvatuspaatos ? this.lapsiService.updateVarhaiskasvatuspaatos(varhaiskasvatuspaatosDTO) :
        this.lapsiService.createVarhaiskasvatuspaatos(varhaiskasvatuspaatosDTO);
      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            if (!this.varhaiskasvatuspaatos) {
              // Close panel if object was created
              this.togglePanel(false);
            }

            this.snackBarService.success(this.i18n.varhaiskasvatuspaatos_save_success);
            this.lapsiService.sendLapsiListUpdate();
            this.varhaiskasvatuspaatos = {...result, varhaiskasvatussuhteet: this.varhaiskasvatussuhdeList};
            this.addObject.emit(this.varhaiskasvatuspaatos);
          },
          error: err => this.errorMessageService.handleError(err, this.snackBarService)
        })
      );
    } else {
      this.disableSubmit();
    }
  }

  deleteVarhaiskasvatuspaatos(): void {
    this.subscriptions.push(
      this.lapsiService.deleteVarhaiskasvatuspaatos(this.varhaiskasvatuspaatos.id).subscribe({
        next: () => {
          this.togglePanel(false);
          this.snackBarService.warning(this.i18n.varhaiskasvatuspaatos_delete_success);
          this.lapsiService.sendLapsiListUpdate();
          this.deleteObject.emit(this.varhaiskasvatuspaatos.id);
        },
        error: err => this.errorMessageService.handleError(err, this.snackBarService)
      })
    );
  }

  hideAddVarhaiskasvatussuhde() {
    this.addVarhaiskasvatussuhdeBoolean = false;
  }

  addVarhaiskasvatussuhde(varhaiskasvatussuhde: LapsiKoosteVakasuhde) {
    this.varhaiskasvatussuhdeList = this.varhaiskasvatussuhdeList.filter(obj => obj.id !== varhaiskasvatussuhde.id);
    this.varhaiskasvatussuhdeList.push(varhaiskasvatussuhde);
    this.varhaiskasvatussuhdeList = this.varhaiskasvatussuhdeList.sort(sortByAlkamisPvm);
    this.updateActiveLapsi();
  }

  deleteVarhaiskasvatussuhte(objectId: number) {
    this.varhaiskasvatussuhdeList = this.varhaiskasvatussuhdeList.filter(obj => obj.id !== objectId);
    this.updateActiveLapsi();
  }

  updateActiveLapsi() {
    const activeLapsi = this.lapsiService.activeLapsi.getValue();
    const activeVarhaiskasvatuspaatos = activeLapsi.varhaiskasvatuspaatokset.find(obj => obj.id === this.varhaiskasvatuspaatos.id);
    activeVarhaiskasvatuspaatos.varhaiskasvatussuhteet = this.varhaiskasvatussuhdeList;
    this.lapsiService.activeLapsi.next(activeLapsi);
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting = false, 2500);
  }

  enableForm() {
    this.isEdit = true;
    this.formGroup.enable();

    if (this.varhaiskasvatuspaatos) {
      this.formGroup.controls.jarjestamismuoto_koodi.disable();
      this.formGroup.controls.vuorohoito_kytkin.disable();
      this.formGroup.controls.paivittainen_vaka_kytkin.disable();
      this.formGroup.controls.kokopaivainen_vaka_kytkin.disable();
      this.formGroup.controls.tuntimaara_viikossa.disable();
      this.formGroup.controls.tilapainen_vaka_kytkin.disable();
    }
  }

  handleJarjestamismuodot(jarjestamismuodot: Array<CodeDTO>) {
    this.jarjestamismuotoKoodisto = jarjestamismuodot;
    let acceptedMuotoLista = jarjestamismuodot.map(jarjestamismuoto => jarjestamismuoto.code_value.toLocaleUpperCase());

    if (this.selectedVakajarjestaja.kunnallinen_kytkin) { // kunta ei voi tallentaa jm04/05
      acceptedMuotoLista = acceptedMuotoLista.filter(jarjestamismuoto => !['JM04', 'JM05'].includes(jarjestamismuoto));
    } else { // yksityinen ei voi tallentaa jm01
      acceptedMuotoLista = acceptedMuotoLista.filter(jarjestamismuoto => jarjestamismuoto !== 'JM01');
    }

    if (this.isPaos) { // paos-kytkin tarjoaa pelkkää JM02/03
      acceptedMuotoLista = acceptedMuotoLista.filter(jarjestamismuoto => ['JM02', 'JM03'].includes(jarjestamismuoto));
    } else { // poistetaan eipaoskytkin lapselta jm02/03
      acceptedMuotoLista = acceptedMuotoLista.filter(jarjestamismuoto => !['JM02', 'JM03'].includes(jarjestamismuoto));
    }

    this.jarjestamismuotoKoodisto = this.jarjestamismuotoKoodisto.map(jarjestamismuotoKoodi => {
      jarjestamismuotoKoodi.code_value = jarjestamismuotoKoodi.code_value.toLocaleUpperCase();
      jarjestamismuotoKoodi.disabled = !acceptedMuotoLista.includes(jarjestamismuotoKoodi.code_value);
      return jarjestamismuotoKoodi;
    });
  }

  changeJarjestamismuoto(jarjestamismuoto: string) {
    this.tilapainenVarhaiskasvatusBoolean = kunnallisetJarjestamismuodot.includes(jarjestamismuoto.toLocaleUpperCase());
    if (this.tilapainenVarhaiskasvatusBoolean && this.isEdit) {
      this.formGroup.get('tilapainen_vaka_kytkin').enable();
    } else {
      this.formGroup.get('tilapainen_vaka_kytkin').disable();
    }
  }

  initDateFilters() {
    if (this.varhaiskasvatuspaatos) {
      this.minStartDate = new Date(this.varhaiskasvatuspaatos.hakemus_pvm);
      this.minEndDate = new Date(this.varhaiskasvatuspaatos.alkamis_pvm);
    }
  }

  vuorohoitoChange(value: boolean) {
    this.formGroup.get('paivittainen_vaka_kytkin').setValue(null);
    this.formGroup.get('kokopaivainen_vaka_kytkin').setValue(null);

    if (value) {
      this.formGroup.get('paivittainen_vaka_kytkin').disable();
      this.formGroup.get('kokopaivainen_vaka_kytkin').disable();
    } else {
      this.formGroup.get('paivittainen_vaka_kytkin').enable();
      this.formGroup.get('kokopaivainen_vaka_kytkin').enable();
    }
  }

  tilapainenVakaChange(value: boolean) {
    const paattymisCtrl = this.formGroup.get('paattymis_pvm');
    if (value) {
      paattymisCtrl.addValidators(this.tilapainenValidator);
    } else {
      paattymisCtrl.removeValidators(this.tilapainenValidator);
    }
    paattymisCtrl.updateValueAndValidity();
  }

  hakemusDateChange(hakemusDate: Moment) {
    this.minStartDate = hakemusDate?.clone().toDate();
    this.minEndDate = this.minEndDate || hakemusDate?.clone().toDate();
    setTimeout(() => this.formGroup.controls.alkamis_pvm?.updateValueAndValidity(), 100);
    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  startDateChange(startDate: Moment) {
    this.minEndDate = startDate?.clone().toDate();
    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
}
