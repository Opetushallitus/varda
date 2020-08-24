import { FormControl, FormGroup, ValidatorFn } from '@angular/forms';

export class VardaFormValidators {

  static validStringFormat(...args) {
    const fc = args[1];
    const regexPattern = args[0].regex;
    const fcValue = fc.value;

    if (!fcValue) {
      return null;
    }

    const regexObj = RegExp(regexPattern);
    const errorObj = { regex: true };

    return !regexObj.test(fcValue) ? errorObj : null;
  }

  static rejectSpecialChars(fc: FormControl) {
    const fcValue = fc.value;
    if (!fcValue) {
      return null;
    }
    const matchAllowedChars = fcValue.match(/^[a-zåäöÅÄÖA-Z0-9\s+-@!]+$/);
    return matchAllowedChars ? null : { rejectSpecialChars: true };
  }

  static rejectSpecialCharsEmail(fc: FormControl) {
    const fcValue = fc.value;
    if (!fcValue) {
      return null;
    }
    const matchAllowedChars = fcValue.match(/^[a-zåäöÅÄÖA-Z0-9_\s+-@!]+$/);
    return matchAllowedChars ? null : { rejectSpecialChars: true };
  }

  static rejectSpecialCharsNames(fc: FormControl) {
    const fcValue = fc.value;
    if (!fcValue) {
      return null;
    }
    const matchAllowedChars = fcValue.match(/^[a-zA-Z0-9\u00c0-\u017e/&'’,+-.:()`´\s-]+$/);
    return matchAllowedChars ? null : { rejectSpecialCharsNames: true };
  }

  static validSSN(fc: FormControl) {
    if (!fc.value) {
      return null;
    }
    const ssnValue = fc.value.trim();
    const dd = parseInt(ssnValue.substring(0, 2));
    const mm = parseInt(ssnValue.substring(2, 4));
    const yy = ssnValue.substring(4, 6);

    const ddIsValid = dd <= 31 && dd > 0;
    const mmIsValid = mm <= 12 && mm > 0;

    const isValidSSN = ssnValue.match(/^[0-9]{6}[\-\+A]{1}[0-9]{3}[0-9ABCDEFHJKLMNPRSTUVWXY]$/);

    return isValidSSN && ssnValue.length === 11 && ddIsValid && mmIsValid ? null : { invalidSSN: true };
  }

  static validOppijanumero(fc: FormControl) {
    try {
      if (!fc.value) {
        return null;
      }
      const oppijanumeroValue = fc.value.trim();
      const oidLengthCorrect = (oppijanumeroValue.length === 26) ? true : false;
      const isHenkiloOid = (oppijanumeroValue.substring(11, 15) === '.24.') ? true : false;
      return isHenkiloOid && oidLengthCorrect ? null : { invalidOppijanumero: true };
    } catch (e) {
      return null;
    }
  }

  static nicknamePartOfFirstname(fg: FormGroup) {
    try {
      const controls = fg.controls;
      const originalFirstnames = controls.firstnames.value;
      const originalNickname = controls.nickname.value;

      if (!originalFirstnames || !originalNickname) {
        return null;
      }

      const trimmedFirstnames = originalFirstnames.trim();
      const trimmedNickname = originalNickname.trim();
      const firstnameParts = trimmedFirstnames.split(' ');
      const nicknameParts = trimmedNickname.split(' ');

      if (nicknameParts.length !== 1) {
        return { nicknameMustBeOneName: true };
      }

      const nickname = nicknameParts[0];
      const acceptedNicknames = [];

      firstnameParts.forEach((v) => {
        const dashedFirstnameParts = v.split('-');
        if (dashedFirstnameParts.length > 1) {
          acceptedNicknames.push(v);
        }
        acceptedNicknames.push(...dashedFirstnameParts);
      });

      return acceptedNicknames.includes(nickname) ? null : { nicknameNotPartOfFirstname: true };
    } catch (e) {
      return null;
    }
  }

  static selectArrMustHaveOneValue(fg: FormGroup) {
    try {
      const controls = fg.controls;
      const selectArr = controls.selectArr.value;
      return selectArr && selectArr[0] ? null : { selectArrMustHaveOneValue: true };
    } catch (e) {
      return null;
    }
  }

  static validOrEmptyIBAN(fc: FormControl) {
    try {
      const ibanValue = fc.value.replace(/ /g, '');
      const ibanLengthCorrect = (ibanValue.length === 18) ? true : false;
      const fiPrefix = ibanValue.substring(0, 2);
      const fiPrefixFound = (fiPrefix.toLowerCase() === 'fi') ? true : false;
      return ibanValue.length === 0 || fiPrefixFound && ibanLengthCorrect ? null : { invalidIBAN: true };
    } catch (e) {
      return null;
    }
  }

  static validHenkiloName(fc: FormControl) {
    try {
      const fcValue = fc.value;
      if (!fcValue) {
        return null;
      }

      const validationObj = {
        nameHasDisallowedCharacters: null
      };

      const trimmedValue = fcValue.replace(/ /g, '');
      const startsWith = trimmedValue.startsWith('-');
      const endsWith = trimmedValue.endsWith('-');
      const hasDoubleDash = trimmedValue.indexOf('--');
      if (hasDoubleDash !== -1 || startsWith || endsWith) {
        validationObj.nameHasDisallowedCharacters = true;
        return validationObj;
      }

      const matchAllowedChars = trimmedValue.match(/^[a-zà-öø-ÿåäöÅÄÖA-ZÀ-ÖØ-ß',-.`´\s-]+$/);
      return matchAllowedChars ? null : validationObj;
    } catch (e) {
      return null;
    }
  }


  static inRange(min: number, max: number): ValidatorFn {
    return (control: FormControl) => {
      if (control.invalid) {
        return null;
      }

      if (control.value < min || control.value > max) {
        return { outOfRange: true };
      }
      return null;
    };
  }

  static remainderOf(number: number): ValidatorFn {
    return (control: FormControl) => {
      if (control.invalid) {
        return null;
      }

      if (control.value % number !== 0) {
        return { divisionOf: true };
      }
      return null;
    };
  }
}
