import { Component, OnInit, Input, OnChanges, Output, EventEmitter } from '@angular/core';
import { VardaFormService } from '../../../core/services/varda-form.service';
import { FormControl, FormGroup, FormArray} from '@angular/forms';
import { IMyDpOptions, IMyInputFocusBlur } from 'mydatepicker';
import { VardaFieldSet, VardaField, VardaWidgetNames, VardaKoodistot } from '../../../utilities/models';
import { VardaKielikoodistoService } from '../../../core/services/varda-kielikoodisto.service';
import { VardaKuntakoodistoService } from '../../../core/services/varda-kuntakoodisto.service';
import { VardaDateService } from '../../../varda-main/services/varda-date.service';
import { TranslateService, LangChangeEvent } from '@ngx-translate/core';
import {VardaMaksunPerusteKoodistoService} from '../../../core/services/varda-maksun-peruste-koodisto.service';

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

  public myDatePickerOptions: IMyDpOptions = {
    dateFormat: 'dd.mm.yyyy',
    indicateInvalidDate: false
  };

  constructor(private vardaFormService: VardaFormService,
    private vardaKielikoodistoService: VardaKielikoodistoService,
    private vardaKuntakoodistoService: VardaKuntakoodistoService,
    private vardaMaksunPerustekoodistoService: VardaMaksunPerusteKoodistoService,
    private vardaDateService: VardaDateService,
    private translateService: TranslateService) {
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

  getOptionDisplayNameByCode(code: string, options?: Array<{code: string}>): string {
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

  getClasses(field: VardaField): string {

    if (this.partOfInline) {
      return 'varda-input-full';
    }

    let classStr = 'varda-input-';
    if (field.styles) {
      if (field.styles.width === '0.1') {
        classStr += '1';
      } else if (field.styles.width === '0.2') {
        classStr += '2';
      } else if (field.styles.width === '0.3') {
        classStr += '3';
      } else if (field.styles.width === '0.4') {
        classStr += '4';
      } else if (field.styles.width === '0.5') {
        classStr += '5';
      } else if (field.styles.width === '0.6') {
        classStr += '6';
      } else if (field.styles.width === '0.7') {
        classStr += '7';
      } else if (field.styles.width === '0.8') {
        classStr += '8';
      } else if (field.styles.width === '0.9') {
        classStr += '9';
      }
    }
    return classStr;
  }

  getErrorTexts(field: VardaField): Array<string> {
    const errorMessages = [];
    const fieldFormControl = this.form.get(field.key);
    const lang = this.translateService.currentLang.toUpperCase();
    const prop = (lang === 'SV') ? 'errorTextSv' : 'errorTextFi';
    if (fieldFormControl.errors) {
      const errorKeys = Object.keys(fieldFormControl.errors);
      errorKeys.forEach((errorKey) => {
        errorMessages.push(field.rules[errorKey]['errorText'][prop]);
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
    this.changedField.emit({field: field, form: this.form, formArrIndex: this.fieldSetIndex, formName: this.formName});
  }

  onSelectValueChange($event: Event, field: VardaField) {
    // Does not take account the case if effected fields are disabled but the modifying field is changeable.
    const target = <HTMLInputElement>event.target;
    if (field.rules && field.rules.modifyExternalFields) {
      const dependentFields = Object.keys(field.rules.modifyExternalFields);
      dependentFields.forEach(dependentField => {
        const dependentFormGroup = this.form.get(dependentField);
        const rule = field.rules.modifyExternalFields[dependentField];
        if (Object.keys(rule).indexOf('disableIfValue') !== -1) {
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

  dateFieldChanged($event: any, fieldset: VardaFieldSet, field: VardaField) {

    if ($event.value === '' && !field.rules.required) {
      return;
    }

    setTimeout(() => {
      const fc = this.form.get(field.key);
      const dateInvalid = {};
      let hasErrors = false;
      if ($event.value === '' && field.rules.required) {
        dateInvalid['required'] = true;
        hasErrors = true;
      }

      if (!$event.valid) {
        dateInvalid['vardaUIDate'] = true;
        hasErrors = true;
      }

      if (field.rules && field.rules.isBefore && $event.valid) {
        const currentDateFieldValue = fc.value;
        const currentDateMoment = this.vardaDateService.uiDateToMoment(currentDateFieldValue);
        const isBeforeFieldKey = field.rules.isBefore.key;
        const isBeforeField = this.vardaFormService.findVardaFieldFromFieldSetsByFieldKey(isBeforeFieldKey, [fieldset]);
        const isBeforeFc = this.form.get(isBeforeFieldKey);
        const isBeforeDateMoment = this.vardaDateService.uiDateToMoment(isBeforeFc.value);
        const currentDateIsBefore = this.vardaDateService.date1IsBeforeDate2(currentDateMoment, isBeforeDateMoment);

        if (!currentDateIsBefore) {
          dateInvalid['isBefore'] = true;
          hasErrors = true;
        } else {
          isBeforeFc.setValidators(this.vardaFormService.getValidators(isBeforeField));
          isBeforeFc.updateValueAndValidity();
        }
      }

      if (field.rules && field.rules.isAfter && $event.valid) {
        const currentDateFieldValue = fc.value;
        const currentDateMoment = this.vardaDateService.uiDateToMoment(currentDateFieldValue);
        const isAfterFieldKey = field.rules.isAfter.key;
        const isAfterField = this.vardaFormService.findVardaFieldFromFieldSetsByFieldKey(isAfterFieldKey, [fieldset]);
        const isAfterFc = this.form.get(isAfterFieldKey);
        const isAfterDateMoment = this.vardaDateService.uiDateToMoment(isAfterFc.value);

        const currentDateIsAfter = this.vardaDateService.date1IsAfterDate2(currentDateMoment, isAfterDateMoment);

        if (!currentDateIsAfter) {
          dateInvalid['isAfter'] = true;
          hasErrors = true;
        } else {
          isAfterFc.setValidators(this.vardaFormService.getValidators(isAfterField));
          isAfterFc.updateValueAndValidity();
        }
      }

      if (field.rules && field.rules.isAfterOrSame && $event.valid) {
        const currentDateFieldValue = fc.value;
        const currentDateMoment = this.vardaDateService.uiDateToMoment(currentDateFieldValue);
        const isAfterOrSameFieldKey = field.rules.isAfterOrSame.key;
        const isAfterOrSameField = this.vardaFormService.findVardaFieldFromFieldSetsByFieldKey(isAfterOrSameFieldKey, [fieldset]);
        const isAfterOrSameFc = this.form.get(isAfterOrSameFieldKey);
        const isAfterOrSameDateMoment = this.vardaDateService.uiDateToMoment(isAfterOrSameFc.value);

        const currentDateisAfterOrSame = this.vardaDateService.date1isAfterOrSameAsDate2(currentDateMoment, isAfterOrSameDateMoment);

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

  dateFieldFocus($eventObj: IMyInputFocusBlur, fieldset: VardaFieldSet, field: VardaField): void {
    if ($eventObj.reason === 1) {
      this.showInstructionText = true;
    } else {
      this.showInstructionText = false;
    }

    this.vardaFormService.highlightDatepickerElement('focus', $eventObj.reason,
    fieldset, field, this.fieldSetName, this.fieldIndex, this.fieldSetIndex);
  }

  dateFieldToggle($eventObj: number, fieldset: VardaFieldSet, field: VardaField): void {
    this.vardaFormService.highlightDatepickerElement('toggle', $eventObj,
    fieldset, field, this.fieldSetName, this.fieldIndex, this.fieldSetIndex);
  }

  formatSelectOptions(): void {
    if (this.field.koodisto === VardaKoodistot.KIELIKOODISTO) {

      this.allSelectOptions = this.vardaKielikoodistoService.getKielikoodistoOptions();

      this.allSelectOptions.forEach((koodistoOption) => {
        try {
          const kielikoodiObj = {};
          const metadataFi = this.vardaKielikoodistoService.getKielikoodistoOptionMetadataByLang(
            koodistoOption.metadata, 'FI');
          let metadataSv = this.vardaKielikoodistoService.getKielikoodistoOptionMetadataByLang(
            koodistoOption.metadata, 'SV');

          if (!metadataSv) {
            metadataSv = metadataFi;
          }

          kielikoodiObj['code'] = koodistoOption.koodiArvo;
          kielikoodiObj['displayName'] = {};
          kielikoodiObj['displayName']['displayNameFi'] = metadataFi.nimi;
          kielikoodiObj['displayName']['displayNameSv'] = metadataSv.nimi;
          this.selectOptions.push(kielikoodiObj);
        } catch (e) {
          console.log(e);
        }
      });

      this.selectOptions.splice(10, 0, '-------------');

    } else if (this.field.koodisto === VardaKoodistot.KUNTAKOODISTO) {
      this.allSelectOptions = this.vardaKuntakoodistoService.getKuntakoodistoOptions();
      this.allSelectOptions.forEach((koodistoOption) => {
        const kuntakoodiObj = {};
        const metadataFi = this.vardaKuntakoodistoService.getKuntaKoodistoOptionMetadataByLang(
          koodistoOption.metadata, 'FI');
        const metadataSv = this.vardaKuntakoodistoService.getKuntaKoodistoOptionMetadataByLang(
          koodistoOption.metadata, 'SV');
        kuntakoodiObj['code'] = koodistoOption.koodiArvo;
        kuntakoodiObj['displayName'] = {};
        kuntakoodiObj['displayName']['displayNameFi'] = metadataFi.nimi;
        kuntakoodiObj['displayName']['displayNameSv'] = metadataSv.nimi;
        this.selectOptions.push(kuntakoodiObj);
      });
    } else if (this.field.koodisto === VardaKoodistot.MAKSUNPERUSTEKOODISTO) {
      this.allSelectOptions = this.vardaMaksunPerustekoodistoService.getKoodistoOptions();
      this.allSelectOptions.forEach((koodistoOption) => {
        const kuntakoodiObj = {};
        const metadataFi = this.vardaMaksunPerustekoodistoService
          .getKoodistoOptionMetadataByLang(koodistoOption.metadata, 'FI');
        const metadataSv = this.vardaMaksunPerustekoodistoService
          .getKoodistoOptionMetadataByLang(koodistoOption.metadata, 'SV');
        kuntakoodiObj['code'] = koodistoOption.koodiArvo.toLowerCase();
        kuntakoodiObj['displayName'] = {};
        kuntakoodiObj['displayName']['displayNameFi'] = metadataFi && metadataFi.nimi;
        kuntakoodiObj['displayName']['displayNameSv'] = metadataSv && metadataSv.nimi;
        this.selectOptions.push(kuntakoodiObj);
      });

      this.currentLang = this.translateService.currentLang;
      this.sortKoodistoOptions(this.selectOptions);

      this.translateService.onLangChange.subscribe((event: LangChangeEvent) => {
        this.currentLang = event.lang;
        this.sortKoodistoOptions(this.selectOptions);
      });
    } else {
      let selectOptions = [];
      this.field.options.forEach((opt) => {
        selectOptions.push({displayName: opt.displayName, code: opt.code});
      });

      this.currentLang = this.translateService.currentLang;
      this.sortKoodistoOptions(selectOptions);

      this.selectOptions = selectOptions;

      this.translateService.onLangChange.subscribe((event: LangChangeEvent) => {
        this.currentLang = event.lang;
        this.sortKoodistoOptions(this.selectOptions);
      });
    }
  }

  sortKoodistoOptions(options: Array<any>): Array<any> {
    const sortByLang = this.currentLang === 'sv' ? 'displayNameSv' : 'displayNameFi';
    options.sort((a, b) => {
      const aOpt = a.displayName[sortByLang].toUpperCase();
      const bOpt = b.displayName[sortByLang].toUpperCase();
      return aOpt.localeCompare(bOpt, this.currentLang);
    });

    return options;
  }

  ngOnChanges() {}

  ngOnInit() {
    try {
      this.ui.isLoading = true;
      if (this.field.widget === VardaWidgetNames.SELECT || this.field.widget === VardaWidgetNames.SELECTARR) {
        this.formatSelectOptions();
      }

      if (this.field.widget === VardaWidgetNames.DATE) {
        this.myDatePickerOptions.ariaLabelInputField = this.getInstructionText(this.field);
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
