import { Injectable } from '@angular/core';

@Injectable()
export class VardaRuleService {

  constructor() { }

  notAllowedIfKeyHasBooleanValue(ruleFields: {[fieldKey: string]: boolean}, formFields: {[formFieldKey: string]: any}): boolean {

    let dependentFieldsHaveValues = false;

    for (const k of Object.keys(ruleFields)) {
      const ruleFieldBooleanValue = ruleFields[k];
      const formFieldValue = formFields[k];

      if (ruleFieldBooleanValue === formFieldValue) {
        dependentFieldsHaveValues = true;
      }
    }

    return dependentFieldsHaveValues;
  }

}
