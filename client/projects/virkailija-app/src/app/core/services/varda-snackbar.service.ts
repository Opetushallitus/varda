import { Injectable } from '@angular/core';
import { MatSnackBar, MatSnackBarConfig } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

export enum SnackbarTimers {
  flash = 2000,
  short = 5000,
  normal = 10000,
  long = 25000,
  xlong = 60000,
  eternal = 3600000,
}

@Injectable()
export class VardaSnackBarService {

  i18n = VirkailijaTranslations;
  defaultAction: string;
  defaultError: string;

  constructor(
    private snackBar: MatSnackBar,
    private translate: TranslateService
  ) {
    this.translate.get([this.i18n.close, this.i18n.error]).subscribe(translations => {
      this.defaultAction = translations[this.i18n.close];
      this.defaultError = translations[this.i18n.error];
    });
  }

  private open(message: string, action?: string, config?: MatSnackBarConfig) {
    this.snackBar.open(
      this.translate.instant(message),
      action ? this.translate.instant(action) : this.defaultAction,
      config
    );
  }

  success(message: string, action?: string, config?: MatSnackBarConfig) {
    const successConfig = {
      ...config,
      panelClass: 'varda-snackbar-success',
      duration: config?.duration || SnackbarTimers.short
    };


    this.open(
      this.translate.instant(message),
      action ? this.translate.instant(action) : this.defaultAction,
      successConfig
    );
  }

  warning(message: string, action?: string, config?: MatSnackBarConfig) {
    const warningConfig = {
      ...config,
      panelClass: 'varda-snackbar-warning',
      duration: config?.duration || SnackbarTimers.short
    };

    this.open(
      this.translate.instant(message),
      action ? this.translate.instant(action) : this.defaultAction,
      warningConfig
    );

  }

  error(message: string, action?: string, config?: MatSnackBarConfig) {
    const errorConfig = {
      ...config,
      panelClass: 'varda-snackbar-error',
      duration: config?.duration || SnackbarTimers.long
    };

    this.open(
      this.translate.instant(message),
      action ? this.translate.instant(action) : this.defaultAction,
      errorConfig
    );
  }

  /**
    * does console.error(message, error) and passes your message to snackbar error(message)
   */
  errorWithConsole(message: string, error: Error) {
    console.error(message, '\n', error.message);
    this.error(message);
  }

  /**
    * errorFromBackend is only for varda-backend-format errors. only shows the first error in the list
    * @remarks
    * expand this with template if you wish to show multiple error-lines
   */
  errorFromBackend(messages: Array<string>, action?: string, config?: MatSnackBarConfig) {
    const errorConfig = {
      ...config,
      panelClass: 'varda-snackbar-error',
      duration: config?.duration || SnackbarTimers.long
    };

    const message = `${this.defaultError}: ${this.translate.instant(messages[0])}`;

    this.open(
      message,
      action ? this.translate.instant(action) : this.defaultAction,
      errorConfig
    );
  }

}
