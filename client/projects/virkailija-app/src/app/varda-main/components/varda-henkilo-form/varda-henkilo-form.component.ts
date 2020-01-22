import {Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges, ViewChild} from '@angular/core';
import {VardaEntityNames, VardaHenkiloDTO, VardaToimipaikkaDTO} from '../../../utilities/models';
import {FormControl, FormGroup, Validators} from '@angular/forms';
import {MatStepper} from '@angular/material';
import {VardaHenkiloService} from '../../services/varda-henkilo.service';
import {VardaApiWrapperService} from '../../../core/services/varda-api-wrapper.service';
import {VardaModalService} from '../../../core/services/varda-modal.service';
import {VardaFormValidators} from '../../../shared/validators/varda-form-validators';
import {VardaVakajarjestajaService} from '../../../core/services/varda-vakajarjestaja.service';
import {TranslateService} from '@ngx-translate/core';
import {VardaErrorMessageService} from '../../../core/services/varda-error-message.service';

declare var $: any;

@Component({
  selector: 'app-varda-henkilo-form',
  templateUrl: './varda-henkilo-form.component.html',
  styleUrls: ['./varda-henkilo-form.component.css']
})
export class VardaHenkiloFormComponent implements OnInit, OnChanges {

  @Input() henkilo: VardaHenkiloDTO;
  @Output() createHenkilo: EventEmitter<any> = new EventEmitter<any>();
  @Output() updateLapsi: EventEmitter<any> = new EventEmitter<any>();
  @Output() deleteLapsi: EventEmitter<any> = new EventEmitter<any>();
  @Output() closeHenkiloForm: EventEmitter<any> = new EventEmitter<any>();
  @Output() valuesChanged: EventEmitter<any> = new EventEmitter();
  @ViewChild('henkiloStepper') henkiloStepper: MatStepper;

  currentHenkilo: VardaHenkiloDTO;
  vardaHenkiloForm: FormGroup;
  henkiloEntitySelection: string;
  henkiloHasRole: boolean;
  henkiloIsLapsi: boolean;
  toimipaikka: VardaToimipaikkaDTO;

  ui: {
    henkiloAddRequestSuccess: boolean,
    henkiloAddRequestFailure: boolean,
    lapsiFormErrors: Array<any>;
    isFetchingHenkilo: boolean,
    isLoading: boolean,
    activeInstructionText: string,
    ssnInstructionText: string,
    firstnamesInsructionText: string,
    lastnamesInstructionText: string
  };

  constructor(private vardaHenkiloService: VardaHenkiloService,
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaModalService: VardaModalService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vardaErrorMessageService: VardaErrorMessageService,
    private translateService: TranslateService) {
    this.ui = {
      henkiloAddRequestSuccess: false,
      henkiloAddRequestFailure: false,
      lapsiFormErrors: [],
      isFetchingHenkilo: false,
      isLoading: false,
      activeInstructionText: '',
      ssnInstructionText: '',
      firstnamesInsructionText: '',
      lastnamesInstructionText: ''
    };

    this.vardaModalService.modalOpenObs('lapsiSuccessModal').subscribe((isOpen: boolean) => {
      if (isOpen) {
        $(`#lapsiSuccessModal`).modal({keyboard: true, focus: true});
        setTimeout(() => {
          $(`#lapsiSuccessModal`).modal('hide');
        }, 2500);
      }
    });

    this.translateService.get([
      'henkiloform.ssninstruction',
      'henkiloform.firstnamesinstruction',
      'henkiloform.lastnamesinstruction',
    ]).subscribe((translations) => {
      this.ui.ssnInstructionText = translations[0];
      this.ui.firstnamesInsructionText = translations[1];
      this.ui.lastnamesInstructionText = translations[2];
    });
  }

  chooseHenkiloEntity(entity: string): void {
    this.henkiloEntitySelection = entity;
  }

  getHenkiloFormData(): any {
    return this.vardaHenkiloForm.value;
  }

  getHenkiloSsnLabel(): string {
    const addWithSsnOrOid = this.vardaHenkiloForm.get('addWithSsnOrOid').value;
    return addWithSsnOrOid ? 'label.ssn' : 'label.oppijanumero';
  }

  getHenkiloSsnInstructionText(): string {
    const addWithSsnOrOid = this.vardaHenkiloForm.get('addWithSsnOrOid').value;
    return addWithSsnOrOid ? 'henkiloform.ssninstruction' : 'henkiloform.oppijanumeroinstruction';
  }

  getSsnPlaceholderText(): string {
    const addWithSsnOrOid = this.vardaHenkiloForm.get('addWithSsnOrOid').value;
    return addWithSsnOrOid ? '012345A678B' : '1.2.246.562.24.XXXXXXXXXXX';
  }

  addWithSsnOrOidChanged($event: any): void {
    const addWithSsn = $event.value;
    let validatorsForSsnOrOid;
    if (addWithSsn) {
      validatorsForSsnOrOid = [Validators.required, VardaFormValidators.validSSN];
    } else {
      validatorsForSsnOrOid = [Validators.required, VardaFormValidators.validOppijanumero];
    }

    const vardaHenkiloFormControls = this.vardaHenkiloForm.controls;
    const vardaHenkiloFormKeys = Object.keys(vardaHenkiloFormControls);
    for (let x = 0; x < vardaHenkiloFormKeys.length; x++) {
      const fcKey = vardaHenkiloFormKeys[x];
      const fc = this.vardaHenkiloForm.get(fcKey);

      if (fcKey === 'ssn') {
        fc.setValue('');
        fc.markAsUntouched();
        fc.setValidators(validatorsForSsnOrOid);
      }

      fc.updateValueAndValidity();
    }
  }

  initExistingHenkiloForm(): void {
    if (this.vardaHenkiloService.henkiloIsLapsi(this.currentHenkilo)) {
      this.henkiloIsLapsi = true;
      this.henkiloHasRole = true;
    }
  }

  lapsiFormValuesChanged(hasChanged: boolean) {
    this.valuesChanged.emit(hasChanged);
  }

  onUpdateLapsi(data: any): void {
    this.updateLapsi.emit(data);
  }

  onDeleteLapsi(data: any): void {
    this.deleteLapsi.emit(data);
  }

  onSaveLapsiSuccess(data: any): void {
    this.ui.henkiloAddRequestSuccess = true;
    this.createHenkilo.emit(data);
    this.vardaModalService.openModal('lapsiSuccessModal', true);
  }

  onSaveLapsiFailure(e: any): void {
    this.ui.henkiloAddRequestFailure = true;
    this.ui.isFetchingHenkilo = false;
    this.ui.isLoading = false;

    this.ui.lapsiFormErrors = [];
    const errorMessageObj = this.vardaErrorMessageService.getErrorMessages(e);
    if (errorMessageObj) {
      this.ui.lapsiFormErrors = errorMessageObj.errorsArr;
    }
  }

  onBlur(): void {
    this.ui.activeInstructionText = '';
  }

  onFocus(field: string): void {
    this.ui.activeInstructionText = field;
  }

  searchHenkilo(): void {
    const henkiloFormData = this.getHenkiloFormData();
    const ssnValue = henkiloFormData.ssn;
    const firstnamesValue = henkiloFormData.firstnames;
    const nicknameValue = henkiloFormData.nickname;
    const lastnameValue = henkiloFormData.lastname;
    this.ui.isFetchingHenkilo = true;
    this.ui.henkiloAddRequestFailure = false;

    const addWithSsnOrOid = this.vardaHenkiloForm.get('addWithSsnOrOid').value;

    this.vardaApiWrapperService.getHenkiloBySsnOrHenkiloOid(ssnValue, addWithSsnOrOid).subscribe((henkilo) => {
      this.currentHenkilo = henkilo;
      this.chooseHenkiloEntity(VardaEntityNames.LAPSI);
      this.ui.isFetchingHenkilo = false;
    }, () => {
      this.vardaApiWrapperService.createHenkiloByHenkiloDetails(ssnValue,
        firstnamesValue, nicknameValue, lastnameValue, addWithSsnOrOid).subscribe(() => {
        setTimeout(() => {
          this.vardaApiWrapperService.getHenkiloBySsnOrHenkiloOid(ssnValue, addWithSsnOrOid).subscribe((fetchedHenkilo) => {
            this.currentHenkilo = fetchedHenkilo;
            this.chooseHenkiloEntity(VardaEntityNames.LAPSI);
            this.ui.isFetchingHenkilo = false;
          }, (ee) => this.onSaveLapsiFailure(ee));
        }, 4000);
      }, (ee) => {
        this.onSaveLapsiFailure(ee);
      });
    });
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.henkilo) {
      this.currentHenkilo = changes.henkilo.currentValue;
      this.initExistingHenkiloForm();
    }
  }

  ngOnInit() {
    this.toimipaikka = this.vardaVakajarjestajaService.getSelectedToimipaikka();
    this.vardaHenkiloForm = new FormGroup({
      addWithSsnOrOid: new FormControl(true),
      ssn: new FormControl('', [Validators.required, VardaFormValidators.validSSN]),
      firstnames: new FormControl('', [Validators.required, VardaFormValidators.validHenkiloName]),
      nickname: new FormControl('', [Validators.required, VardaFormValidators.validHenkiloName]),
      lastname: new FormControl('', [Validators.required, VardaFormValidators.validHenkiloName])
    }, VardaFormValidators.nicknamePartOfFirstname);

    this.vardaHenkiloForm.valueChanges.subscribe(() => {
      if (this.vardaHenkiloForm.dirty) {
        this.valuesChanged.emit(true);
      }
    });
  }

}
