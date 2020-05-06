import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class VardaErrorMessageService {

  errorMessageKeys = {
    'Not a valid kunta_koodi.': 'field.kunta_koodi.invalid',
    'Not a valid kieli_koodi.': 'field.kieli_koodi.invalid',
    'Not a valid toimintapainotus_koodi.': 'field.toimintapainotus_koodi.invalid',
    'Not a valid Finnish phone number.': 'field.puhelinnumero.invalid',
    'Not a valid tutkinto_koodi.': 'field.tutkinto_koodi.invalid',
    'Not a valid kasvatusopillinen_jarjestelma_koodi.': 'field.kasvatusopillinen_jarjestelma_koodi.invalid',
    'Not a valid toimintamuoto_koodi.': 'field.toimintamuoto_koodi.invalid',
    'Not a valid jarjestamismuoto_koodi.': 'field.jarjestamismuoto_koodi.invalid',
    'Not a valid opiskeluoikeudentila_koodi.': 'field.opiskeluoikeudentila_koodi.invalid',
    'paattymis_pvm must be after alkamis_pvm (or same).': 'paattymis_pvm must be after alkamis_pvm',
    'Cannot delete varhaiskasvatuspaatos. There are objects referencing it that need to be deleted first.': 'field.vakapaatos_cannot_be_deleted',
    'Postinumero is incorrect.': 'field.postinumero.invalid',
    'hakemus_pvm must be before alkamis_pvm (or same).': 'field.hakemus_pvm.before_alkamis_pvm',
    'Changing of varhaiskasvatuspaatos is not allowed': 'field.vakasuhde-vakapaatos-change-not-allowed',
    'Not a valid IBAN code.': 'field.iban.invalid',
    'Toimipaikan nimi has disallowed characters.': 'alert.toimipaikka-has-disallowed-characters',
    'Incorrect format.': 'alert.toimipaikka-has-disallowed-characters',
    'varhaiskasvatussuhde.alkamis_pvm must be after varhaiskasvatuspaatos.alkamis_pvm (or same)': 'varhaiskasvatussuhde.alkamis_pvm must be after varhaiskasvatuspaatos.alkamis_pvm',
    'varhaiskasvatuspaatos.paattymis_pvm must be after varhaiskasvatussuhde.paattymis_pvm (or same)': 'varhaiskasvatuspaatos.paattymis_pvm must be after varhaiskasvatussuhde.paattymis_pvm',
    'varhaiskasvatussuhde.alkamis_pvm must be before varhaiskasvatuspaatos.paattymis_pvm (or same)': 'varhaiskasvatussuhde.alkamis_pvm must be before varhaiskasvatuspaatos.paattymis_pvm',
    'varhaiskasvatussuhde must have paattymis_pvm because varhaiskasvatuspaatos has paattymis_pvm': 'field.varhaiskasvatussuhde_paattymis_pvm.required',
    'Combination of nimi and vakajarjestaja fields should be unique': 'fields.unique.nimi-vakajarjestaja',
    'Tämän luvun on oltava vähintään 1.0.': 'field.minvalue.one',
    'varhaiskasvatussuhde.alkamis_pvm cannot be same or after toimipaikka.paattymis_pvm.': 'varhaiskasvatussuhde.paivamaarat cannot be after toimipaikka.paattymis_pvm',
    'varhaiskasvatussuhde.paattymis_pvm cannot be after toimipaikka.paattymis_pvm.': 'varhaiskasvatussuhde.paivamaarat cannot be after toimipaikka.paattymis_pvm',
    'Name must have at least 2 characters.': 'alert.toimipaikka-minimum-length',
    'Maximum 2 consecutively repeating special characters are allowed.': 'alert.toimipaikka-maximum-repeating-special-characters',
    'Invalid code for paos-lapsi.': 'field.jarjestamismuoto_koodi.paos-lapsi-invalid-code',
    'There is no active paos-agreement to this toimipaikka.': 'alert.paos-lapsi-creation-failed',
    'There is no active paos-agreement.': 'alert.paos-lapsi-creation-failed',
    'Vakajarjestaja is different than paos_organisaatio for lapsi.': 'alert.vakajarjestaja-eri-kuin-lapsen-paos-toimija',
    'Arvo tulee olla vähintään 3 merkkiä pitkä.': 'field.postiosoite.invalid',
    'oma_organisaatio cannot be same as paos_organisaatio.': 'alert.oma_organisaatio_same_as_paos',
    'Date must be greater than or equal to 2000-01-01.': 'field.date-after-1999',
  };

  dynamicErrorMessageKeys = {
    'has already 3 overlapping varhaiskasvatuspaatos on the defined time range.': 'field.lapsi-has-already-three-overlapping-vakapaatos',
    'has already 3 overlapping varhaiskasvatussuhde on the defined time range.': 'field.lapsi-has-already-three-overlapping-vakasuhde',
    'Ensure this field has no more than 20 characters.': 'field.maxlength.20',
    'Se till att detta fält inte har fler än 20 tecken.': 'field.maxlength.20',
    'Arvo saa olla enintään 20 merkkiä pitkä.': 'field.maxlength.20',
    'Ensure this field has no more than 200 characters.': 'field.maxlength.200',
    'Se till att detta fält inte har fler än 200 tecken.': 'field.maxlength.200',
    'Arvo saa olla enintään 200 merkkiä pitkä.': 'field.maxlength.200'
  };

  /*
  DIFFERENT CASES
  "kayntiosoite_postinumero": [
    "00000 : Postinumero is incorrect."
  ],
  "hakemus_pvm": [
    "hakemus_pvm must be before alkamis_pvm (or same)."
  ]
  {"tuntimaara_viikossa":[
    "Tässä luvussa voi olla yhteensä enintään 4 numeroa."
  ]}
  {"asiointikieli_koodi": {
    "0": [
      "SEPO : Not a valid kieli_koodi."
    ]
  }}
  {"error message"}
  */

  constructor() { }

  getErrorMessages(errorResponse: any): any {
    const errorObj = errorResponse;
    let formattedErrors = null;
    if (errorObj) {
      formattedErrors = this.formatErrorHttpResponse(errorObj);
    }
    return formattedErrors;
  }

  handleArrayErrorMsg(errorEntry: any): any {
    let translatedErrorMsg = '';

    const errorContentsParts = typeof (errorEntry[0]) === 'string' ? errorEntry[0].split(':') : ['', errorEntry[0].detail];
    const errorMsgFirstPart = errorContentsParts[0];
    const errorMsgSecondPart = errorContentsParts[1];

    const dynamicErrorMsg = this.getFromDynamicErrorMessages(errorMsgFirstPart);

    if (dynamicErrorMsg) {
      translatedErrorMsg = dynamicErrorMsg;
    }

    if (this.errorMessageKeys[errorMsgFirstPart]) {
      translatedErrorMsg = this.errorMessageKeys[errorMsgFirstPart];
    }

    if (errorMsgSecondPart) {
      const errorMessageKey = errorMsgSecondPart.trim();
      if (this.errorMessageKeys[errorMessageKey]) {
        translatedErrorMsg = this.errorMessageKeys[errorMessageKey];
      }
    }

    return translatedErrorMsg;
  }

  getFromDynamicErrorMessages(errorMessageKey: string): string {
    let rv = '';
    for (const x in this.dynamicErrorMessageKeys) {
      if (this.dynamicErrorMessageKeys.hasOwnProperty(x)) {
        const subStr = x;
        const foundInErrorMsg = errorMessageKey.indexOf(subStr);
        if (foundInErrorMsg !== -1) {
          rv = this.dynamicErrorMessageKeys[x];
          break;
        }
      }
    }
    return rv;
  }

  createErrorObjEntry(key: string, msgContent: string): any {
    const errorKey = `field.${key}.label`;
    const errorMsg = msgContent;
    return {
      key: errorKey,
      msg: errorMsg
    };
  }

  formatErrorHttpResponse(errorObj: any): any {
    const rv = [];
    errorObj = errorObj.error;
    const errorKeys = Object.keys(errorObj);
    errorKeys.forEach((key) => {
      try {
        const errorEntry = errorObj[key];
        let errorContent = '';
        let translatedErrorMsgObj;

        if (Array.isArray(errorObj[key])) {
          errorContent = this.handleArrayErrorMsg(errorEntry);
          translatedErrorMsgObj = this.createErrorObjEntry(key, errorContent);
          rv.push(translatedErrorMsgObj);

        } else if (typeof errorEntry === 'string') {
          translatedErrorMsgObj = this.createErrorObjEntry(key, this.errorMessageKeys[errorEntry]);
          rv.push(translatedErrorMsgObj);

        } else {
          const errorObjKeys = Object.keys(errorEntry);
          errorObjKeys.forEach((k) => {
            errorContent = this.handleArrayErrorMsg(errorEntry[k]);
            translatedErrorMsgObj = this.createErrorObjEntry(key, errorContent);
            rv.push(translatedErrorMsgObj);
          });

        }
      } catch (e) {
        console.log(e);
      }
    });
    return { errorsArr: rv };
  }
}
