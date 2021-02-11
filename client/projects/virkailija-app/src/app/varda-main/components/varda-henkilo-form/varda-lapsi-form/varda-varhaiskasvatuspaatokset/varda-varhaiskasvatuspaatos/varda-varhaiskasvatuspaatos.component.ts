import { Component, OnInit, OnChanges, Input, Output, EventEmitter, ElementRef, OnDestroy } from '@angular/core';
import { FormGroup, FormControl, Validators, AbstractControl, ValidatorFn } from '@angular/forms';
import * as moment from 'moment';
import { Moment } from 'moment';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi, VardaVarhaiskasvatuspaatosDTO, VardaVarhaiskasvatussuhdeDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { LapsiListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaDateService } from 'projects/virkailija-app/src/app/varda-main/services/varda-date.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';
import { filter, distinctUntilChanged } from 'rxjs/operators';
import { VardaKoodistoService, KoodistoEnum, CodeDTO } from 'varda-shared';
import { TranslateService } from '@ngx-translate/core';
import { VardaHenkiloFormAccordionAbstractComponent } from '../../../varda-henkilo-form-accordion/varda-henkilo-form-accordion.abstract';


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
export class VardaVarhaiskasvatuspaatosComponent extends VardaHenkiloFormAccordionAbstractComponent implements OnInit, OnChanges, OnDestroy {
  @Input() lapsi: LapsiListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() lapsitiedotTallentaja: boolean;
  @Input() varhaiskasvatuspaatos: VardaVarhaiskasvatuspaatosDTO;
  @Output() closeAddVarhaiskasvatuspaatos = new EventEmitter<boolean>(true);
  @Output() changedVarhaiskasvatuspaatos = new EventEmitter<boolean>(true);
  i18n = VirkailijaTranslations;
  element: ElementRef;
  expandPanel: boolean;
  varhaiskasvatussuhteet: Array<VardaVarhaiskasvatussuhdeDTO>;
  isEdit: boolean;
  addVarhaiskasvatussuhdeBoolean: boolean;
  varhaiskasvatuspaatosForm: FormGroup;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  isSubmitting = new BehaviorSubject<boolean>(false);
  varhaiskasvatuspaatosFormErrors: Observable<Array<ErrorTree>>;
  subscriptions: Array<Subscription> = [];
  jarjestamismuotoKoodisto: Array<JarjestamismuodotCode>;
  tilapainenVarhaiskasvatusBoolean: boolean;
  minStartDate: Date;
  minEndDate: Date;
  private henkilostoErrorService: VardaErrorMessageService;

  constructor(
    private el: ElementRef,
    private lapsiService: VardaLapsiService,
    private modalService: VardaModalService,
    private koodistoService: VardaKoodistoService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private snackBarService: VardaSnackBarService,
    private translateService: TranslateService
  ) {
    super();
    this.element = this.el;
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.varhaiskasvatuspaatosFormErrors = this.henkilostoErrorService.initErrorList();

    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
  }


  ngOnInit() {

    this.koodistoService.getKoodisto(KoodistoEnum.jarjestamismuoto).subscribe(koodisto => this.handleJarjestamismuodot(koodisto.codes));

    this.varhaiskasvatuspaatosForm = new FormGroup({
      id: new FormControl(this.varhaiskasvatuspaatos?.id),
      lahdejarjestelma: new FormControl(this.varhaiskasvatuspaatos?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      lapsi: new FormControl(this.varhaiskasvatuspaatos?.lapsi || `/api/v1/lapset/${this.lapsi.id}/`),
      toimipaikka_oid: new FormControl(this.varhaiskasvatuspaatos ? null : this.henkilonToimipaikka?.organisaatio_oid),
      hakemus_pvm: new FormControl(this.varhaiskasvatuspaatos ? moment(this.varhaiskasvatuspaatos?.hakemus_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      alkamis_pvm: new FormControl(this.varhaiskasvatuspaatos ? moment(this.varhaiskasvatuspaatos?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.varhaiskasvatuspaatos ? moment(this.varhaiskasvatuspaatos?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
      jarjestamismuoto_koodi: new FormControl(this.varhaiskasvatuspaatos?.jarjestamismuoto_koodi.toLocaleUpperCase(), Validators.required),
      vuorohoito_kytkin: new FormControl(this.varhaiskasvatuspaatos?.vuorohoito_kytkin, Validators.required),
      paivittainen_vaka_kytkin: new FormControl(this.varhaiskasvatuspaatos?.paivittainen_vaka_kytkin, Validators.required),
      kokopaivainen_vaka_kytkin: new FormControl(this.varhaiskasvatuspaatos?.kokopaivainen_vaka_kytkin, Validators.required),
      // tilapainen will be enabled later CSCVARDA-2040
      tilapainen_vaka_kytkin: new FormControl(this.varhaiskasvatuspaatos?.tilapainen_vaka_kytkin, Validators.required),
      tuntimaara_viikossa: new FormControl(this.varhaiskasvatuspaatos?.tuntimaara_viikossa, [Validators.pattern('^\\d+([,.]\\d{1})?$'), Validators.min(1), Validators.max(120), Validators.required]),
    });

    if (this.varhaiskasvatuspaatos) {
      this.changeJarjestajismuoto(this.varhaiskasvatuspaatos.jarjestamismuoto_koodi);
      this.checkFormErrors(this.lapsiService, 'vakapaatos', this.varhaiskasvatuspaatos?.id);
    }

    if (!this.lapsitiedotTallentaja || this.varhaiskasvatuspaatos) {
      this.disableForm();
    } else {
      this.enableForm();
    }

    this.initDateFilters();

    this.subscriptions.push(
      this.varhaiskasvatuspaatosForm.statusChanges
        .pipe(filter(() => !this.varhaiskasvatuspaatosForm.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true)),
      this.varhaiskasvatuspaatosForm.get('tilapainen_vaka_kytkin').valueChanges
        .subscribe((value: boolean) => this.tilapainenVakaChange(value))
    );
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  ngOnChanges() {
    if (this.varhaiskasvatuspaatos) {
      this.getVarhaiskasvatussuhteet();
    } else {
      this.togglePanel(true);
    }
  }

  saveVarhaiskasvatuspaatos(form: FormGroup): void {
    this.isSubmitting.next(true);
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const varhaiskasvatuspaatosDTO: VardaVarhaiskasvatuspaatosDTO = {
        ...form.value,
        hakemus_pvm: form.value.hakemus_pvm.format(VardaDateService.vardaApiDateFormat),
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      if (this.varhaiskasvatuspaatos) {
        this.lapsiService.updateVarhaiskasvatuspaatos(varhaiskasvatuspaatosDTO).subscribe({
          next: varhaiskasvatuspaatosData => {
            this.changedVarhaiskasvatuspaatos.emit();
            this.snackBarService.success(this.i18n.varhaiskasvatuspaatos_save_success);
            this.lapsiService.sendLapsiListUpdate();
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      } else {
        this.lapsiService.createVarhaiskasvatuspaatos(varhaiskasvatuspaatosDTO).subscribe({
          next: varhaiskasvatuspaatosData => {
            this.togglePanel(false, true);
            this.snackBarService.success(this.i18n.varhaiskasvatuspaatos_save_success);
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      }

    } else {
      this.disableSubmit();
    }
  }

  togglePanel(open: boolean, refreshList?: boolean) {
    this.expandPanel = open;

    if (!open || refreshList) {
      this.disableForm();
      this.closeAddVarhaiskasvatuspaatos?.emit(refreshList);
      if (refreshList) {
        this.lapsiService.sendLapsiListUpdate();
      }
    }
  }

  deleteVarhaiskasvatuspaatos(): void {
    this.lapsiService.deleteVarhaiskasvatuspaatos(this.varhaiskasvatuspaatos.id).subscribe({
      next: deleted => {
        this.togglePanel(false, true);
        this.snackBarService.warning(this.i18n.varhaiskasvatuspaatos_delete_success);
      },
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  getVarhaiskasvatussuhteet(): void {
    this.lapsiService.getVarhaiskasvatussuhteet(this.varhaiskasvatuspaatos.id).subscribe({
      next: varhaiskasvatussuhdeData => {
        this.varhaiskasvatussuhteet = varhaiskasvatussuhdeData;
      },
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  closeVarhaiskasvatussuhde(refresh?: boolean): void {
    this.addVarhaiskasvatussuhdeBoolean = false;
    if (refresh) {
      this.getVarhaiskasvatussuhteet();
    }
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting.next(false), 2500);
  }

  disableForm() {
    this.isEdit = false;
    this.varhaiskasvatuspaatosForm.disable();
    this.modalService.setFormValuesChanged(false);
  }

  enableForm() {
    this.isEdit = true;
    this.varhaiskasvatuspaatosForm.enable();

    if (this.varhaiskasvatuspaatos) {
      this.varhaiskasvatuspaatosForm.controls.jarjestamismuoto_koodi.disable();
      this.varhaiskasvatuspaatosForm.controls.vuorohoito_kytkin.disable();
      this.varhaiskasvatuspaatosForm.controls.paivittainen_vaka_kytkin.disable();
      this.varhaiskasvatuspaatosForm.controls.kokopaivainen_vaka_kytkin.disable();
      this.varhaiskasvatuspaatosForm.controls.tuntimaara_viikossa.disable();
      this.varhaiskasvatuspaatosForm.controls.tilapainen_vaka_kytkin.disable();
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

    if (this.lapsi.paos_organisaatio_oid) { // paos-kytkin tarjoaa pelkkää JM02/03
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

  changeJarjestajismuoto(jarjestamismuoto: string) {

    this.tilapainenVarhaiskasvatusBoolean = kunnallisetJarjestamismuodot.includes(jarjestamismuoto.toLocaleUpperCase());
    if (this.tilapainenVarhaiskasvatusBoolean) {
      this.varhaiskasvatuspaatosForm.get('tilapainen_vaka_kytkin').enable();
    } else {
      this.varhaiskasvatuspaatosForm.get('tilapainen_vaka_kytkin').disable();
    }
  }

  initDateFilters() {
    if (this.varhaiskasvatuspaatos) {
      this.minStartDate = new Date(this.varhaiskasvatuspaatos.hakemus_pvm);
      this.minEndDate = new Date(this.varhaiskasvatuspaatos.alkamis_pvm);
    }
  }

  vuorohoitoChange(value: boolean) {
    this.varhaiskasvatuspaatosForm.get('paivittainen_vaka_kytkin').setValue(null);
    this.varhaiskasvatuspaatosForm.get('kokopaivainen_vaka_kytkin').setValue(null);

    if (value) {
      this.varhaiskasvatuspaatosForm.get('paivittainen_vaka_kytkin').disable();
      this.varhaiskasvatuspaatosForm.get('kokopaivainen_vaka_kytkin').disable();
    } else {
      this.varhaiskasvatuspaatosForm.get('paivittainen_vaka_kytkin').enable();
      this.varhaiskasvatuspaatosForm.get('kokopaivainen_vaka_kytkin').enable();
    }
  }

  tilapainenVakaChange(value: boolean) {
    const tilapainenValidator = (): ValidatorFn => {
      return (control: AbstractControl) => {
        return control.value ? null : { tilapainen: true };
      };
    };

    const paattymisCtrl = this.varhaiskasvatuspaatosForm.get('paattymis_pvm');
    if (value) {
      paattymisCtrl.setValidators(tilapainenValidator());
    } else {
      paattymisCtrl.setValidators(null);
    }

    paattymisCtrl.updateValueAndValidity();
  }

  hakemusDateChange(hakemusDate: Moment) {
    this.minStartDate = hakemusDate?.clone().toDate();
    this.minEndDate = this.minEndDate || hakemusDate?.clone().toDate();
    setTimeout(() => this.varhaiskasvatuspaatosForm.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  startDateChange(startDate: Moment) {
    this.minEndDate = startDate?.clone().toDate();
    setTimeout(() => this.varhaiskasvatuspaatosForm.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

}
