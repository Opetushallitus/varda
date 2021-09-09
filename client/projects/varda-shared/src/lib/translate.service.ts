import { TranslateLoader } from '@ngx-translate/core';
import { Observable } from 'rxjs';
import { TranslationDTO, AngularTranslateDTO, SupportedLanguage } from './models/translation-dto';
import { LoadingHttpService } from './loading-http.service';
import { VardaApiServiceInterface } from './models/vardaApiService.interface';
import { HttpHeaders } from '@angular/common/http';
import { CommonTranslations } from '../common-translations.enum';


interface LocalizationCache {
  timestamp: number;
  translations: AngularTranslateDTO;
}

export class VardaTranslateLoader implements TranslateLoader {
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
        this.fetchTranslations(lang).subscribe(translation => {
          preparedTranslation.next(this.handleTranslations(translation, lang));
          preparedTranslation.complete();
        }, () => {
          if (existingCache) {
            preparedTranslation.next(existingCache.translations);
            preparedTranslation.complete();
          } else if (attemptNr < 2) {
            setTimeout(() => this.getTranslation(lang, attemptNr++), 200);
          } else {
            console.error('Failed to load translations');
            preparedTranslation.next({});
            preparedTranslation.complete();
          }
        });
      }
    });
  }


  fetchTranslations(lang: SupportedLanguage): Observable<Array<TranslationDTO>> {
    return this.http.get(`${this.localizationApi}/?category=${this.translationCategory}&locale=${lang}`, null, new HttpHeaders());
  }


  handleTranslations(translations: Array<TranslationDTO>, lang: SupportedLanguage): AngularTranslateDTO {
    const translationEnum = { ...this.appApi.getTranslationEnum(), ...CommonTranslations };
    const i18nTranslations: AngularTranslateDTO = {};
    const i18nExcess = [];
    const enumMissing = Object.values(translationEnum).filter(value => !translations.some(translation => translation.key === value));

    translations.forEach(translation => {
      if (translation.key.startsWith('backend.')) {
        i18nTranslations[translation.key] = translation.value;
      } else if (!Object.values(translationEnum).some(value => value === translation.key)) {
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
