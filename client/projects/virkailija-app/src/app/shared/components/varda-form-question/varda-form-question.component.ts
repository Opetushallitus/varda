import { Component, OnInit, Input, OnChanges, Output, EventEmitter } from '@angular/core';
import { VardaFormService } from '../../../core/services/varda-form.service';
import { FormControl, FormGroup, FormArray } from '@angular/forms';
import { VardaFieldSet, VardaField, VardaWidgetNames } from '../../../utilities/models';
import { VardaDateService } from '../../../varda-main/services/varda-date.service';
import { TranslateService, LangChangeEvent } from '@ngx-translate/core';
import { VardaSelectOption } from '../../../utilities/models/varda-select-option.model';
import { VardaDatepickerEvent } from '../varda-datepicker/varda-datepicker.component';
import { KoodistoEnum, VardaKoodistoService } from 'varda-shared';

@Component({
  selector: 'app-varda-form-question',
  templateUrl: './varda-form-question.component.html',
  styleUrls: ['./varda-form-question.component.css']
})
export class VardaFormQuestionComponent implements OnInit, OnChanges {

  @Input() field: VardaField;
  @Input() fieldIndex: number;
  @Input() fieldSet: VardaFieldSet;
  @Input() fieldSetIndex: number;
  @Input() fieldSetName: string;
  @Input() form: FormGroup;
  @Input() partOfInline: boolean;
  @Input() formName: string;
  @Input() isReadOnly?: boolean;
  @Output() changedField: EventEmitter<any> = new EventEmitter();

  showInstructionText: boolean;
  isRequired: boolean;

  allSelectOptions: Array<any> = [];
  selectOptions: Array<any> = [];
  currentLang: string;

  VardaWidgetNames = VardaWidgetNames;

  ui: {
    isLoading: boolean
  };

  constructor(
    private vardaFormService: VardaFormService,
    private vardaDateService: VardaDateService,
    private translateService: TranslateService,
    private koodistoService: VardaKoodistoService
  ) {
    this.showInstructionText = false;
    this.ui = {
      isLoading: false
    };
    this.isReadOnly = !!this.isReadOnly;
  }

  addSelectArrControl(): void {
    const fg = <FormGroup>this.form.get(this.field.key);
    const fa = <FormArray>fg.get('selectArr');
    fa.push(new FormControl());
  }

  removeSelectArrControl(index: number): void {
    const fg = <FormGroup>this.form.get(this.field.key);
    const fa = <FormArray>fg.get('selectArr');
    fa.removeAt(index);
  }

  getDisplayName(field: VardaField): string {
    let rv = '';
    const lang = this.translateService.currentLang.toUpperCase();
    const prop = (lang === 'SV') ? 'displayNameSv' : 'displayNameFi';

    if (field.displayName && field.displayName[prop]) {
      rv = field.displayName[prop];
    }
    return rv;
  }

  getSelectedCheckboxCodes(checkboxObj) {
    return Object.keys(checkboxObj).filter(key => checkboxObj[key]);
  }

  getOptionDisplayNameByCode(code: string, options?: Array<{ code: string }>): string {
    const selectOptions = options || this.selectOptions;
    const selectedOption = code && selectOptions.filter(option => option.code === code)[0];
    return selectedOption && this.getOptionDisplayName(selectedOption);
  }

  getOptionDisplayName(option: any): string {
    let rv = '';
    const lang = this.translateService.currentLang.toUpperCase();
    const prop = (lang === 'SV') ? 'displayNameSv' : 'displayNameFi';

    if (option.displayName && option.displayName[prop]) {
      rv = option.displayName[prop];
    }
    return `${rv} (${option.code})`;
  }

  getPlaceholderText(field: VardaField): string {
    let rv = '';
    const lang = this.translateService.currentLang.toUpperCase();
    const prop = (lang === 'SV') ? 'placeholderSv' : 'placeholderFi';
    if (field.placeholder && field.placeholder[prop]) {
      rv = field.placeholder[prop];
    }
    return rv;
  }

  getInstructionText(field: VardaField): string {
    let rv = '';
    const lang = this.translateService.currentLang.toUpperCase();
    const prop = (lang === 'SV') ? 'instructionTextSv' : 'instructionTextFi';
    if (field.instructionText && field.instructionText[prop]) {
      rv = field.instructionText[prop];
    }
    return rv;
  }

  getErrorTexts(field: VardaField): Array<string> {
    const errorMessages = [];
    const fieldFormControl = this.form.get(field.key);
    const lang = this.translateService.currentLang.toUpperCase();
    const prop = (lang === 'SV') ? 'errorTextSv' : 'errorTextFi';
    if (fieldFormControl.errors) {
      const errorKeys = Object.keys(fieldFormControl.errors);
      errorKeys.forEach((errorKey) => {
        // Skip mat-datepicker error
        if (errorKey !== 'matDatepickerParse') {
          errorMessages.push(field.rules[errorKey]['errorText'][prop]);
        }
      });
    }
    return errorMessages;
  }

  onBlur(field: VardaField): void {
    this.showInstructionText = false;
  }

  onFocus(field: VardaField): void {
    this.showInstructionText = true;
  }

  onInputValueChanged(field: VardaField): void {
    this.changedField.emit({ field: field, form: this.form, formArrIndex: this.fieldSetIndex, formName: this.formName });
  }

  onSelectValueChange($event: Event, field: VardaField) {
    // Does not take account the case if effected fields are disabled but the modifying field is changeable.
    const target = <HTMLInputElement>$event.target;
    if (field.rules && field.rules.modifyExternalFields) {
      const dependentFields = Object.keys(field.rules.modifyExternalFields);
      dependentFields.forEach(dependentField => {
        const dependentFormGroup = this.form.get(dependentField);
        const rule = field.rules.modifyExternalFields[dependentField];
        if (dependentFormGroup && Object.keys(rule).indexOf('disableIfValue') !== -1) {
          if (target.value && target.value.indexOf(rule['disableIfValue']) !== -1) {
            dependentFormGroup.disable();
            dependentFormGroup.setValue(rule.replaceValue);
          } else {
            dependentFormGroup.enable();
          }
        }
      });
    }
  }

  dateFieldChanged($event: VardaDatepickerEvent, fieldset: VardaFieldSet, field: VardaField) {
    if ($event.valid === true && !$event.value && !field.rules.required) {
      return;
    }

    setTimeout(() => {
      const fc = this.form.get(field.key);
      const dateInvalid = {};
      let hasErrors = false;
      if (!$event.value && field.rules.required) {
        dateInvalid['required'] = true;
        hasErrors = true;
      }

      if (!$event.valid) {
        dateInvalid['vardaUIDate'] = true;
        hasErrors = true;
      }

      if (field.rules && field.rules.isBefore && $event.valid) {
        const isBeforeFieldKey = field.rules.isBefore.key;
        const isBeforeField = this.vardaFormService.findVardaFieldFromFieldSetsByFieldKey(isBeforeFieldKey, [fieldset]);
        const isBeforeFc = this.form.get(isBeforeFieldKey);
        const currentDateIsBefore = this.vardaDateService.date1IsBeforeDate2(fc.value, isBeforeFc.value);

        if (!currentDateIsBefore) {
          dateInvalid['isBefore'] = true;
          hasErrors = true;
        } else {
          isBeforeFc.setValidators(this.vardaFormService.getValidators(isBeforeField));
          isBeforeFc.updateValueAndValidity();
        }
      }

      if (field.rules && field.rules.isAfter && $event.valid) {
        const isAfterFieldKey = field.rules.isAfter.key;
        const isAfterField = this.vardaFormService.findVardaFieldFromFieldSetsByFieldKey(isAfterFieldKey, [fieldset]);
        const isAfterFc = this.form.get(isAfterFieldKey);

        const currentDateIsAfter = this.vardaDateService.date1IsAfterDate2(fc.value, isAfterFc.value);

        if (!currentDateIsAfter) {
          dateInvalid['isAfter'] = true;
          hasErrors = true;
        } else {
          isAfterFc.setValidators(this.vardaFormService.getValidators(isAfterField));
          isAfterFc.updateValueAndValidity();
        }
      }

      if (field.rules && field.rules.isAfterOrSame && $event.valid) {
        const isAfterOrSameFieldKey = field.rules.isAfterOrSame.key;
        const isAfterOrSameField = this.vardaFormService.findVardaFieldFromFieldSetsByFieldKey(isAfterOrSameFieldKey, [fieldset]);
        const isAfterOrSameFc = this.form.get(isAfterOrSameFieldKey);

        const currentDateisAfterOrSame = this.vardaDateService.date1isAfterOrSameAsDate2(fc.value, isAfterOrSameFc.value);

        if (!currentDateisAfterOrSame) {
          dateInvalid['isAfterOrSame'] = true;
          hasErrors = true;
        } else {
          isAfterOrSameFc.setValidators(this.vardaFormService.getValidators(isAfterOrSameField));
          isAfterOrSameFc.updateValueAndValidity();
        }
      }

      if (hasErrors) {
        this.form.get(field.key).setErrors(dateInvalid);
      } else {
        this.form.get(field.key).setErrors(null);
      }

      this.form.updateValueAndValidity();
    });
  }

  dateFieldInstructions(focus: boolean): void {
    this.showInstructionText = focus;
  }

  formatSelectOptions(): void {
    const options = this.field.options.map(option => {
      return { displayName: option.displayName, code: option.code };
    });

    this.currentLang = this.translateService.currentLang;

    this.selectOptions = options;

    if (this.field.koodisto === KoodistoEnum.kieli) {
      this.selectOptions.splice(VardaKoodistoService.getNumberOfPrimaryLanguages(), 0, '-------------');
    } else {
      this.sortOptions(options);
    }
  }

  sortOptions(options: Array<VardaSelectOption>): Array<VardaSelectOption> {
    return options.sort((a, b) => a.code.localeCompare(b.code));
  }

  ngOnChanges() { }

  ngOnInit() {
    try {
      this.ui.isLoading = true;
      if (this.field.widget === VardaWidgetNames.SELECT || this.field.widget === VardaWidgetNames.SELECTARR) {
        this.formatSelectOptions();
      }

      if (this.field.rules && this.field.rules.required) {
        this.isRequired = true;
      }

      if (this.field.isReadonly
        && [VardaWidgetNames.TEXTAREA, VardaWidgetNames.CHECKBOX, VardaWidgetNames.BOOLEANRADIO].indexOf(this.field.widget) !== -1) {
        this.form.disable();
      }

      this.ui.isLoading = false;
    } catch (e) {
      console.error(e);
    }
  }
}
