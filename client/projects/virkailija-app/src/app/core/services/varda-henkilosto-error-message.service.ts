import { Inject, Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { FormGroup } from '@angular/forms';
import { VardaErrorMessageService } from './varda-error-message.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaSnackBarService } from './varda-snackbar.service';
import { KoodistoEnum, VardaKoodistoService } from 'varda-shared';
import { AppModule } from '../../app.module';
import { TranslateService } from '@ngx-translate/core';

interface VardaErrorLine {
  [key: string]: Array<string | VardaErrorMessage> | VardaErrorLine;
}

interface VardaErrorTranslation {
  language: string;
  description: string;
}

interface VardaErrorMessage {
  error_code: string;
  description: string;
  translations: Array<VardaErrorTranslation>;
}

interface VardaErrorResponse {
  status?: number;
  error: VardaErrorLine;
}

export interface ErrorValue {
  errorCode: string;
  errorTranslation: string;
  dynamicValue: string;
}

export interface ErrorTree {
  keys: Array<string>;
  values: Array<ErrorValue>;
}

@Injectable({
  providedIn: 'root'
})
export class HenkilostoErrorMessageService {
  private errorList$ = new BehaviorSubject<Array<ErrorTree>>(null);
  private errorLines: Array<ErrorTree> = [];
  private errorMessageKeys = {};

  constructor(private translateService: TranslateService) {
    const vardaErrorMessageService = new VardaErrorMessageService();
    this.errorMessageKeys = {
      ...vardaErrorMessageService.errorMessageKeys,
      ...vardaErrorMessageService.dynamicErrorMessageKeys,
      ...this.errorMessageKeys,
    };
  }

  public static formIsValid(form: FormGroup): boolean {
    if (form.valid) {
      return true;
    }

    Object.keys(form.controls).some(key => {
      if (form.controls[key]?.errors) {
        form.controls[key].setErrors({ ...form.controls[key].errors, scrollTo: true });
        return true;
      }
    });

    return false;
  }

  private loopThrough(error: object | Array<string> | string, errorTree: ErrorTree = { keys: [], values: [] }) {
    if (Array.isArray(error)) {
      errorTree.values = error.map(text => this.parseBackendError(text));
      this.errorLines.push(errorTree);
    } else if (typeof (error) === 'string') {
      errorTree.values.push(this.parseBackendError(error));
      this.errorLines.push(errorTree);
    } else {
      Object.keys(error).forEach(key => {
        this.loopThrough(error[key], { ...errorTree, keys: [...errorTree.keys, key] });
      });
    }
  }

  private parseBackendError(error: VardaErrorMessage | string): ErrorValue {
    let errorCode, errorTranslation, dynamicValue;
    if (typeof error === 'object' && error !== null) {
      errorCode = error.error_code;
      errorTranslation = this.getErrorTranslation(error);
      if (errorTranslation) {
        // If translation was found, show: errorTranslation (errorCode)
        errorTranslation = errorTranslation + ` (${errorCode})`;
      } else {
        // If no translation was found, show: errorCode
        errorTranslation = errorCode;
      }
      if (errorCode.startsWith('DY')) {
        dynamicValue = this.parseDynamicValue(errorCode, error.description);
        if (errorTranslation) {
          // Translations include {{}} signifying dynamic value position
          errorTranslation = errorTranslation.replace(/{{}}/g, dynamicValue);
        }
      }
    } else {
      errorCode = error;
    }

    return {
      errorCode: errorCode,
      errorTranslation: errorTranslation,
      dynamicValue: dynamicValue
    };
  }

  private getErrorTranslation(error: VardaErrorMessage): string {
    const currentLang = this.translateService.currentLang;
    return error.translations.find(errorTranslation => {
      return errorTranslation.language.toLocaleLowerCase() === currentLang.toLocaleLowerCase();
    })?.description;
  }

  private checkFormErrors(formGroup: FormGroup) {
    this.errorLines.forEach(line => line.keys.forEach(key => formGroup.controls[key]?.setErrors({ backend: line.values, scrollTo: true })));
  }

  private parseDynamicValue(errorCode: string, errorDescription: string): string {
    /**
     * Parses dynamic error messages returned from Varda backend. If dynamic error messages are added or modified
     * in backend (error_messages.py), any modifications should be reflected here.
     */
    let regex;
    switch (errorCode) {
      case 'DY001':
        regex = /no more than (\d+) characters/;
        break;
      case 'DY002':
        regex = /at least (\d+) characters/;
        break;
      case 'DY003':
        regex = /no more than (\d+) items/;
        break;
      case 'DY004':
        regex = /greater than or equal to ([\d.]+?)[.]/;
        break;
      case 'DY005':
        regex = /less than or equal to ([\d.]+?)[.]/;
        break;
      case 'DY006':
        regex = /no more than (\d+) decimal places/;
        break;
      case 'DY007':
        regex = /no more than (\d+) digits in total/;
        break;
      default:
        return null;
    }

    const match = errorDescription.match(regex);
    if (match.length > 1) {
      return match[1];
    }

    return null;
  }

  resetErrorList(): void {
    this.errorList$.next(null);
  }

  initErrorList(): Observable<Array<ErrorTree>> {
    return this.errorList$;
  }

  handleError(response: VardaErrorResponse, snackBar?: VardaSnackBarService, formGroup?: FormGroup): void {
    console.error(response.status, response.error);
    const generalErrors = [404, 500, 504];
    this.errorLines = [];

    if (generalErrors.includes(response?.status)) {
      const generalError: ErrorTree = {
        keys: ['server'],
        values: [{
          errorCode: 'UI002',
          errorTranslation: this.translateService.instant('backend.api-timeout-or-not-found'),
          dynamicValue: null
        }]
      };
      this.errorLines.push(generalError);
    } else {
      this.loopThrough(response.error);
      if (formGroup) {
        this.checkFormErrors(formGroup);
      }
    }
    this.errorList$.next(this.errorLines);

    if (snackBar) {
      const errorFlat: Array<ErrorValue> = [].concat(...this.errorLines.map(line => line.values));
      snackBar.errorFromBackend(errorFlat);
    }
  }
}
