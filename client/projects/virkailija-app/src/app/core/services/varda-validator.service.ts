import { Injectable } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { VardaFormService } from './varda-form.service';
import { VardaField, VardaFieldSet } from '../../utilities/models';
import { VardaRuleService } from './varda-rule.service';

@Injectable()
export class VardaValidatorService {

  private notAllowedIfKeyHasBooleanValue = 'notAllowedIfKeyHasBooleanValue';
  field: VardaField;
  fieldSets: Array<VardaFieldSet>;
  form: FormGroup;

  constructor(private vardaRuleService: VardaRuleService, private vardaFormService: VardaFormService) { }

  initFieldStates(fieldSets: Array<VardaFieldSet>, form: FormGroup): void {
    fieldSets.forEach((fieldSet) => {
      if (fieldSet.fields && fieldSet.fields.length > 0) {
        fieldSet.fields.forEach((fieldObj) => {
          if (fieldObj.rules && fieldObj.rules.dependentFields) {
            this.validate(fieldObj, fieldSets, form);
          }
        });
      }
    });
  }

  validate(field: VardaField, fieldSets: Array<VardaFieldSet>, form: FormGroup): void {
    const fieldRules = field.rules;
    if (fieldRules.dependentFields) {
      const dependentFields = fieldRules.dependentFields;
      for (const dependentFieldKey of Object.keys(dependentFields)) {
        const dependentFieldRules = dependentFields[dependentFieldKey];
        this.checkRules(dependentFieldKey, dependentFieldRules, fieldSets, form);
      }
    }
  }

  checkRules(fieldKey: string, rules: {[ruleKey: string]: any}, fieldSets: Array<VardaFieldSet>, form: FormGroup): void {
    for (const ruleKey of Object.keys(rules)) {
      const rule = rules[ruleKey];
      const ruleFormFields = this.getRuleFormFields(rule, form);
      const dependentFieldFc = this.vardaFormService.findFormControlFromFormGroupByFieldKey(fieldKey, form);
      const dependentField = this.vardaFormService.findVardaFieldFromFieldSetsByFieldKey(fieldKey, fieldSets);

      if (ruleKey === this.notAllowedIfKeyHasBooleanValue) {
        const resultForDependentField = this.vardaRuleService.notAllowedIfKeyHasBooleanValue(rule, ruleFormFields);
        if (resultForDependentField) {
          dependentFieldFc.setValue(false);
          dependentField.hidden = true;
        } else {
          dependentField.hidden = false;
        }
      }

      dependentFieldFc.updateValueAndValidity();
    }
  }

  getRuleFormFields(ruleFields: any, form: FormGroup): {[key: string]: any} {
    const fields = {};
    for (const fieldKey of Object.keys(ruleFields)) {
      const formCtrl = this.vardaFormService.findFormControlFromFormGroupByFieldKey(fieldKey, form);
      if (formCtrl) {
        fields[fieldKey] = formCtrl.value;
      }
    }
    return fields;
  }
}
