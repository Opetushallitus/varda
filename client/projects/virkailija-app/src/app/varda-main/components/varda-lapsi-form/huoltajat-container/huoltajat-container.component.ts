import {Component, EventEmitter, forwardRef, Input, OnInit, Output} from '@angular/core';
import {VardaApiWrapperService} from '../../../../core/services/varda-api-wrapper.service';
import {VardaFieldsetArrayContainer} from '../../../../utilities/models/varda-fieldset.model';
import {forkJoin} from 'rxjs';
import {HuoltajaDTO} from '../../../../utilities/models/dto/varda-maksutieto-dto.model';
import {VardaUtilityService} from '../../../../core/services/varda-utility.service';
import {VardaFormService} from '../../../../core/services/varda-form.service';
import {VardaValidatorService} from '../../../../core/services/varda-validator.service';
import {
  AbstractControl,
  ControlValueAccessor,
  FormArray,
  FormGroup,
  NG_VALIDATORS,
  NG_VALUE_ACCESSOR,
  ValidationErrors,
  Validator
} from '@angular/forms';
import { MatRadioChange } from '@angular/material/radio';

enum HuoltajaInputOption {
  Hetu = 'hetu',
  Oppijanumero = 'oppijanumero',
}

@Component({
  selector: 'app-huoltajat-container',
  templateUrl: './huoltajat-container.component.html',
  styleUrls: ['./huoltajat-container.component.css'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => HuoltajatContainerComponent),
      multi: true
    },
    {
      provide: NG_VALIDATORS,
      useExisting: forwardRef(() => HuoltajatContainerComponent),
      multi: true
    }
  ]
})
export class HuoltajatContainerComponent implements OnInit, ControlValueAccessor, Validator {
  @Input() initialHuoltajat: Array<HuoltajaDTO>;
  @Output() huoltajat: EventEmitter<Array<HuoltajaDTO>> = new EventEmitter(true);
  @Input() isReadOnly: boolean;

  HuoltajaInputOption: typeof HuoltajaInputOption = HuoltajaInputOption;

  isEditing: boolean;

  huoltajaFieldSetTemplate: VardaFieldsetArrayContainer;
  huoltajaFieldsetObj: object;
  huoltajaFormGroup: FormGroup;
  huoltajaValinta: Array<string>;
  get huoltajaFormArr(): FormArray {
    return <FormArray>this.huoltajaFormGroup.get('huoltajat');
  }

  getHuoltajaFormGroup(control: AbstractControl, id: string) {
    return <FormGroup>control.get(id);
  }

  constructor(private vardaApiWrapperService: VardaApiWrapperService,
              private vardaUtilityService: VardaUtilityService,
              private vardaFormService: VardaFormService,
              private vardaValidatorService: VardaValidatorService) {
    this.huoltajaFieldsetObj = {};
    this.huoltajaFormGroup = new FormGroup({
      huoltajat: new FormArray([]),
    });
    this.isEditing = true;
  }

  ngOnInit() {
    this.isEditing = !!this.initialHuoltajat.length;
    this.huoltajaValinta = this.initialHuoltajat
      .map(huoltaja => !!huoltaja.henkilotunnus
        ? HuoltajaInputOption.Hetu
        : HuoltajaInputOption.Oppijanumero);
    if (!this.huoltajaValinta.length) {
      this.huoltajaValinta = [HuoltajaInputOption.Hetu];
    }

    forkJoin([
      this.vardaApiWrapperService.getHuoltajaFormFieldSets(),
    ]).subscribe((data) => {
      this.huoltajaFieldSetTemplate = data[0];
      const huoltajaFormGroups = this.initialHuoltajat.map((huoltaja, idx) => this.initHuoltajaFormGroup(huoltaja, idx));
      if (!huoltajaFormGroups.length) {
        huoltajaFormGroups.push(this.initHuoltajaFormGroup(null, 0));
      }
      this.huoltajaFormArr.reset();
      huoltajaFormGroups.forEach((fg, idx) => this.huoltajaFormArr.setControl(idx, fg));
      this.huoltajaFormArr.valueChanges
        .subscribe(huoltajat => this.huoltajat.emit(huoltajat.map(this.huoltajaFieldsetToDto.bind(this))));
    });
  }

  huoltajaFieldsetToDto(huoltajaFieldsets, idx) {
    const huoltaja = this.huoltajaValinta[idx] === HuoltajaInputOption.Hetu
      ? huoltajaFieldsets['huoltaja_henkilotunnuksella']
      : huoltajaFieldsets['huoltaja_oppijanumerolla'];
    const huoltajaDto = new HuoltajaDTO();
    if (huoltaja) {
      huoltajaDto.henkilo_oid = huoltaja.henkilo_oid;
      huoltajaDto.sukunimi = huoltaja.sukunimi;
      huoltajaDto.etunimet = huoltaja.etunimet;
      huoltajaDto.henkilotunnus = huoltaja.henkilotunnus;
    }
    return huoltajaDto;
  }

  addNewHuoltaja() {
    this.huoltajaValinta.push(HuoltajaInputOption.Hetu);
    const newHuoltajaForm = this.initHuoltajaFormGroup(null, this.huoltajaFormArr.length);
    this.huoltajaFormArr.push(newHuoltajaForm);
  }

  private initHuoltajaFormGroup(huoltaja: HuoltajaDTO, idx: number) {
    const selected = this.huoltajaValinta[idx] === this.HuoltajaInputOption.Hetu
      ? 'huoltaja_henkilotunnuksella'
      : 'huoltaja_oppijanumerolla';
    const huoltajaFieldsets = this.vardaUtilityService.deepcopyArray(this.huoltajaFieldSetTemplate.fieldsets)
      .filter(fieldset => fieldset.id === selected);
    this.huoltajaFieldsetObj[idx] = huoltajaFieldsets;
    const huoltajaFormGroup = this.vardaFormService.initFieldSetFormGroup(huoltajaFieldsets, huoltaja);
    this.vardaValidatorService.initFieldStates(huoltajaFieldsets, huoltajaFormGroup);
    return huoltajaFormGroup;
  }

  setHuoltajavalinta($event: MatRadioChange, idx: number) {
    this.huoltajaValinta[idx] = $event.value;
    this.huoltajaFormArr.setControl(idx, this.initHuoltajaFormGroup(null, idx));
  }

  deleteUnsavedHuoltaja(huoltajaIdx: number) {
    this.huoltajaFormArr.removeAt(huoltajaIdx);
  }

  isAllowedAddNewHuoltaja() {
    return this.huoltajaFormGroup.valid;
  }

  /* ControlValueAccessor methods */
  registerOnChange(fn: any): void {
    this.huoltajaFormGroup.valueChanges.subscribe((...arg) => {
      return fn(arg);
    });
  }

  registerOnTouched(fn: any): void {
  }

  setDisabledState(isDisabled: boolean): void {
    isDisabled
      ? this.huoltajaFormGroup.disable()
      : this.huoltajaFormGroup.enable();
  }

  writeValue(obj: any): void {
    if (obj) {
      this.huoltajaFormGroup.setValue(obj, {emitEvent: false});
    }
  }
  /* ControlValueAccessor methods end */

  /* Validator methods */
  registerOnValidatorChange(fn: () => void): void {
  }

  validate(control: AbstractControl): ValidationErrors | null {
    // When form is disabled it is not valid so .valid and .invalid are false.
    return this.huoltajaFormGroup.valid || this.huoltajaFormGroup.disabled
      ? null
      : { invalidForm: {valid: false, message: 'huoltajat form fields are invalid'}};
  }
  /* Validator methods end*/
}
