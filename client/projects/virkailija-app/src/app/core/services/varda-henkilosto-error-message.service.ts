import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { FormGroup } from '@angular/forms';
import { VardaErrorMessageService } from './varda-error-message.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaSnackBarService } from './varda-snackbar.service';

interface VardaErrorLine {
  [key: string]: Array<string> | VardaErrorLine;
}

interface VardaErrorResponse {
  error: VardaErrorLine;
}

export interface ErrorTree {
  keys: Array<string>;
  values: Array<string>;
}

@Injectable({
  providedIn: 'root'
})
export class HenkilostoErrorMessageService {
  private errorList$ = new BehaviorSubject<Array<ErrorTree>>(null);
  private errorLines: Array<ErrorTree> = [];
  private errorMessageKeys = {};
  private i18n = VirkailijaTranslations;

  constructor() {
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
      errorTree.values = error.map(text => this.getErrorByKey(text));
      this.errorLines.push(errorTree);
    } else if (typeof (error) === 'string') {
      errorTree.values.push(this.getErrorByKey(error));
      this.errorLines.push(errorTree);
    } else {
      Object.keys(error).forEach(key => {
        this.loopThrough(error[key], { ...errorTree, keys: [...errorTree.keys, key] });
      });
    }
  }

  private getErrorByKey(key: string) {
    return this.errorMessageKeys[key] || `backend.${key}`;
  }

  private checkFormErrors(formGroup: FormGroup) {
    this.errorLines.forEach(line => line.keys.forEach(key => formGroup.controls[key]?.setErrors({ backend: line.values, scrollTo: true })));
  }


  resetErrorList(): void {
    this.errorList$.next(null);
  }

  initErrorList(): Observable<Array<ErrorTree>> {
    return this.errorList$;
  }

  handleError(response: VardaErrorResponse, snackBar?: VardaSnackBarService, formGroup?: FormGroup): void {
    console.error(response.error);

    this.errorLines = [];
    this.loopThrough(response.error);
    this.errorList$.next(this.errorLines);

    if (formGroup) {
      this.checkFormErrors(formGroup);
    }

    if (snackBar) {
      const errorFlat: Array<string> = [].concat(...this.errorLines.map(line => line.values));
      snackBar.errorFromBackend(errorFlat);
    }
  }

}
