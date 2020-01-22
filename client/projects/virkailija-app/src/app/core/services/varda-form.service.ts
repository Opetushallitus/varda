import { Injectable } from '@angular/core';
import { AbstractControl, FormControl, FormGroup, FormArray, Validators, ValidatorFn } from '@angular/forms';
import {
  VardaFieldSet,
  VardaField,
  VardaWidgetNames } from '../../utilities/models';
import { VardaFormValidators } from '../../shared/validators/varda-form-validators';
import { VardaVakajarjestajaService } from './varda-vakajarjestaja.service';
import { VardaDateService } from '../../varda-main/services/varda-date.service';

@Injectable()
export class VardaFormService {

  fieldSets: Array<VardaFieldSet>;

  private vardaDatepickerFocusSelector = 'varda-date-focus';
  private highlightContainerSelector = 'varda-highlight-container';
  private fieldSetSelector = 'varda-fieldset';

  constructor(private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vardaDateService: VardaDateService) { }

  createFieldSetFormGroup(): FormGroup {
    return new FormGroup({});
  }

  initFieldSetFormGroup(fieldSets: Array<VardaFieldSet>, entityToEdit: any): FormGroup {
    const formControllers: any = {};
    const isEdit = !!entityToEdit;
    fieldSets.forEach((fieldSet) => {
      const fieldSetFg = this.createFieldSetFormGroup();

      fieldSet.fields.forEach((field) => {
        if (this.isHiddenOnCreate(field, isEdit)) {
          fieldSet.fields = fieldSet.fields.filter(obj => obj !== field);
        } else {
          let existingValue = (field.key === 'varhaiskasvatuspaikat' && isEdit) ? '0' : '';
          if (entityToEdit && entityToEdit[field.key]) {
            existingValue = entityToEdit[field.key];
          }
          const fc = this.createControl(field, existingValue, isEdit);
          this.setValue(fc, field, existingValue);

          fieldSetFg.addControl(field.key, fc);
        }
      });
      formControllers[fieldSet.id] = fieldSetFg;
    });
    return new FormGroup(formControllers);
  }

  isHiddenOnCreate(field: VardaField, isEdit: boolean): boolean {
    return field.rules && field.rules.hiddenOnCreate && !isEdit;
  }

  createControl(field: VardaField, value?: any, isEdit?: boolean): AbstractControl {
    let fc: AbstractControl;
    if (field.widget === VardaWidgetNames.DATE) {
      fc = new FormControl('');
    } else if (field.widget === VardaWidgetNames.SELECTARR) {
      const group = new FormGroup({});
      const selectFormArr = new FormArray([]);
      if (value && value.length > 0) {
        value.forEach((val) => {
          selectFormArr.push(new FormControl());
        });
      } else {
        selectFormArr.push(new FormControl());
      }
      group.addControl('selectArr', selectFormArr);
      group.setValidators(this.getValidators(field));
      fc = group;
    } else if (field.widget === VardaWidgetNames.CHECKBOXGROUP) {
      const checkboxGroup = new FormGroup({});
      field.options.forEach((item) => {
        checkboxGroup.addControl(item.code, new FormControl());
      });
      fc = checkboxGroup;
    } else {
      fc = new FormControl('', this.getValidators(field));
    }

    const isDisabledOnEdit = this.isDisabledOnEdit(field, isEdit);
    if (isDisabledOnEdit) {
      fc.disable();
    }

    return fc;
  }

  isDisabledOnEdit(field: VardaField, isEdit: boolean): boolean {
    let rv = false;
    if (field.rules && field.rules.disabledOnEdit && isEdit) {
      rv = true;
    }
    return rv;
  }

  setValue(fc: AbstractControl, field: VardaField, value: any): void {
    if (field.widget === VardaWidgetNames.DATE) {
      field.value = value && this.vardaDateService.vardaDateToUIStrDate(value);
      value = value ? this.vardaDateService.vardaDateToUIDate(value) : null;
    } else if (field.widget === VardaWidgetNames.AUTOCOMPLETEONE) {
      value = value ? value : null;
    } else if (field.widget === VardaWidgetNames.AUTOCOMPLETEMANY) {
      value = value ? value : null;
    } else if (field.widget === VardaWidgetNames.SELECT) {
      value = value ? value : null;
    } else if (field.widget === VardaWidgetNames.AUTOCOMPLETEONEARR) {
      value = value && value.length > 0 ? value[0] : null;
    } else if (field.widget === VardaWidgetNames.CHECKBOX ||
      field.widget === VardaWidgetNames.BOOLEANRADIO) {
      value = !!value;
    } else if (field.widget === VardaWidgetNames.CHECKBOXGROUP) {
      const valObj = {};
      field.options.forEach((option) => {
        let optionFound = false;
        if (value) {
          value.forEach((val) => {
            if (val === option.code) {
              optionFound = true;
            }
          });
          valObj[option.code] = optionFound;
        } else {
          valObj[option.code] = false;
        }
      });
      value = valObj;
    } else if (field.widget === VardaWidgetNames.SELECTARR) {
      const valObj = { selectArr: []};
      valObj.selectArr[0] = null;
      if (value) {
        value.forEach((val, index) => {
          valObj.selectArr[index] = val;
        });
      }
      value = valObj;
    }
    fc.setValue(value);
    if (!field.value) {
      field.value = value;
    }
  }

  getValidators(field: VardaField): Array<ValidatorFn> {
    const validators = [];
    if (field.rules) {
      const rules = field.rules;

      if (rules.required) {
        validators.push(Validators.required);
      }

      if (rules.maxlength) {
        validators.push(Validators.maxLength(rules.maxlength.acceptedValue));
      }

      if (rules.minlength) {
        validators.push(Validators.minLength(rules.minlength.acceptedValue));
      }

      if (rules.regex) {
        validators.push(VardaFormValidators.validStringFormat.bind(null, {regex: rules.regex.acceptedValue}));
      }

      if (rules.rejectSpecialChars) {
        validators.push(VardaFormValidators.rejectSpecialChars);
      }

      if (rules.rejectSpecialCharsEmail) {
        validators.push(VardaFormValidators.rejectSpecialCharsEmail);
      }

      if (rules.rejectSpecialCharsNames) {
        validators.push(VardaFormValidators.rejectSpecialCharsNames);
      }

      if (rules.selectArrMustHaveOneValue) {
        validators.push(VardaFormValidators.selectArrMustHaveOneValue);
      }

      if (rules.min) {
        validators.push(Validators.min(rules.min.acceptedValue));
      }
    }
    return validators;
  }

  findFormControlFromFormGroupByFieldKey(formFieldKey: string, form: FormGroup): AbstractControl {
    let fc;
    const fieldSetControlKeys = Object.keys(form.controls);
    if (fieldSetControlKeys.length > 0) {
      for (const fieldSetCtrlKey of fieldSetControlKeys) {
        const fieldSetCtrl = <FormGroup>form.controls[fieldSetCtrlKey];
        const fieldFormControlKeys = Object.keys(fieldSetCtrl.controls);
        for (const fieldFormCtrlKey of fieldFormControlKeys) {
          if (formFieldKey === fieldFormCtrlKey) {
            fc = <any> fieldSetCtrl.controls[fieldFormCtrlKey];
            break;
          }
        }

        if (fc) {
          break;
        }
      }
    }
    return fc;
  }

  findVardaFieldFromFieldSetsByFieldKey(fieldKey: string, fieldSets: Array<VardaFieldSet>): VardaField {
    let field;
    fieldSets.forEach((fieldSet) => {
      if (fieldSet.fields && fieldSet.fields.length > 0) {
        fieldSet.fields.forEach((fieldItem) => {
          if (fieldItem.key === fieldKey) {
            field = fieldItem;
            return;
          }
        });
      }
      if (field) {
        return;
      }
    });
    return field;
  }

  getFieldSetFormGroup(fieldSet: VardaFieldSet, vardaForm: FormGroup): FormGroup {
    return <FormGroup> vardaForm.controls[fieldSet.id];
  }

  getDatepickerElem(field: VardaField, fieldSetName: string, fieldIndex: number, fieldSetIndex: number): Element {
    return document.querySelector(`my-date-picker[name="${field.key}${fieldSetName}${fieldSetIndex}"]`);
  }

  getDatepickerWrapper(field: VardaField, fieldSetName: string, fieldIndex: number, fieldSetIndex: number): Element {
    return document.querySelector(`my-date-picker[name="${field.key}${fieldSetName}${fieldSetIndex}"] .mydp`);
  }

  highlightDatepickerElement(type: string,
    highlight: number,
    fieldSet: VardaFieldSet,
    field: VardaField,
    fieldSetName: string,
    fieldIndex: number,
    fieldSetIndex: number): void {
    this.removeHighlight(Array.from(this.getFieldSets()), this.highlightContainerSelector);
    let condition = false;
    if (type === 'focus') {
      condition = (highlight === 1) ? true : false;
    } else {
      condition = (highlight === 1 || highlight === 2) ? true : false;
    }
    const datepickerWrapper = this.getDatepickerWrapper(field, fieldSetName, fieldIndex, fieldSetIndex);
    const datepickerElem = this.getDatepickerElem(field, fieldSetName, fieldIndex,  fieldSetIndex);

    this.addHighlightToContainer(datepickerElem['dataset']['parentContainer']);
    if (condition) {
      datepickerWrapper.classList.add(this.vardaDatepickerFocusSelector);
    } else {
      datepickerWrapper.classList.remove(this.vardaDatepickerFocusSelector);
    }
  }

  addHighlightToContainer(parentContainerSelector: string): void {
    if (parentContainerSelector) {
      const parent = document.getElementById(`${parentContainerSelector}`);
      parent.classList.add(this.highlightContainerSelector);
    }
  }

  removeHighlight(elements: Array<Element>, cssClass: string): void {
    elements.forEach((el: HTMLElement) => el.classList.remove(cssClass));
  }

  getFieldSets(): NodeListOf<Element> {
    return document.querySelectorAll(`.${this.fieldSetSelector}`);
  }
}
