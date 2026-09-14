import { Injectable } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { CommonTranslations } from '../common-translations.enum';

@Injectable({
  providedIn: 'root',
})
export class HelperService {
  private translateService: TranslateService;
  private translations: Record<string, string> = {};

  constructor() { }

  setTranslateService(translateService: TranslateService) {
    this.translateService = translateService;
    const translationKeys = Object.values(CommonTranslations);
    this.translateService.stream(translationKeys).subscribe(values => {
      this.translations = values;
    });
  }

  getTranslation(key: string): string {
    const translation = this.translations[key];
    if (translation === undefined) {
      console.error(`Translation missing in varda-shared for key: ${key}`);
    }
    return translation;
  }
}
