import { VardaFieldErrorText } from './varda-field-error-text.model';

export class VardaFieldRules {
  required?: VardaFieldRule;
  maxlength?: VardaFieldRule;
  minlength?: VardaFieldRule;
  regex?: VardaFieldRule;
  rejectSpecialChars?: VardaFieldRule;
  rejectSpecialCharsEmail?: VardaFieldRule;
  rejectSpecialCharsNames?: VardaFieldRule;
  vardaUIDate?: VardaFieldRule;
  isAfter?: VardaFieldRule;
  isAfterOrSame?: VardaFieldRule;
  isBefore?: VardaFieldRule;
  min?: VardaFieldRule;
  dependentFields?: {[key: string]: {[ruleKey: string]: any}};
  selectArrMustHaveOneValue?: VardaFieldRule;
  disabledOnEdit?: VardaFieldRule;
  hiddenOnCreate?: VardaFieldRule;
  modifyExternalFields?: {[key: string]: {disableIfValue: string; replaceValue: string}};
}

export class VardaFieldRule {
  key?: string;
  acceptedValue?: any;
  errorText?: VardaFieldErrorText;
}
