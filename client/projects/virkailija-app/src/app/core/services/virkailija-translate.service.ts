import { TranslateLoader } from '@ngx-translate/core';
import { Observable } from 'rxjs';
import { LoadingHttpService, AngularTranslateDTO, SupportedLanguage, TranslationDTO } from 'varda-shared';
import { VardaApiServiceInterface } from 'projects/varda-shared/src/lib/dto/vardaApiService.interface';
import { HttpHeaders } from '@angular/common/http';

interface LocalizationCache {
  timestamp: number;
  translations: AngularTranslateDTO;
}

export class VirkailijaTranslateLoader implements TranslateLoader {
  translationCategory: string;
  localizationApi: string;

  constructor(private http: LoadingHttpService, private appApi: VardaApiServiceInterface) {
    this.translationCategory = appApi.getTranslationCategory();
    this.localizationApi = appApi.getLocalizationApi();
  }

  getTranslation(lang: SupportedLanguage, attemptNr = 0): Observable<AngularTranslateDTO> {
    return new Observable(preparedTranslation => {
      const existingCache: LocalizationCache = JSON.parse(localStorage.getItem(`${this.translationCategory}.${lang}`));

      if (Date.now() - existingCache?.timestamp < 300000) {
        preparedTranslation.next(existingCache.translations);
        preparedTranslation.complete();
      } else {
        this.fetchJson(lang).subscribe(angularTranslation =>
          this.fetchTranslations(lang).subscribe(translation => {
            preparedTranslation.next(this.handleTranslations(angularTranslation, translation, lang));
            preparedTranslation.complete();
          }, () => {
            if (attemptNr < 4) {
              setTimeout(() => this.getTranslation(lang, attemptNr++), 400);
            } else {
              console.error('Failed to load translations');
              preparedTranslation.next({});
              preparedTranslation.complete();
            }
          })
        );
      }
    });
  }

  fetchTranslations(lang: SupportedLanguage): Observable<Array<TranslationDTO>> {
    return this.http.get(`${this.localizationApi}/?category=${this.translationCategory}&locale=${lang}`, null, new HttpHeaders());
  }

  fetchJson(lang: SupportedLanguage): Observable<AngularTranslateDTO> {
    return this.http.get(`assets/i18n/${lang}.json`);
  }

  handleTranslations(existingTranslations: AngularTranslateDTO, translations: Array<TranslationDTO>, lang: SupportedLanguage): AngularTranslateDTO {
    const translationEnum = this.appApi.getTranslationEnum();
    const i18nTranslations = { ...existingTranslations };
    const i18nExcess = [];
    const enumMissing = Object.values(translationEnum).filter(expectedKey => !translations.some(translation => translation.key === expectedKey));

    translations.forEach(translation => {
      if (translation.key.startsWith('backend.')) {
        i18nTranslations[translation.key] = translation.value;
      } else if (!Object.values(translationEnum).some(expectedKey => expectedKey === translation.key)) {
        i18nExcess.push(translation.key);
      } else {
        i18nTranslations[translation.key] = translation.value;
      }
    });

    if (i18nExcess.length) {
      console.log(`Excess '${lang}' translations:`, i18nExcess);
    }

    if (enumMissing.length) {
      console.log(`Missing '${lang}' translations:`, enumMissing);
    }

    const localizationCache: LocalizationCache = { timestamp: Date.now(), translations: i18nTranslations };
    localStorage.setItem(`${this.translationCategory}.${lang}`, JSON.stringify(localizationCache));

    return i18nTranslations;
  }

}
