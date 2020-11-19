import { TranslateLoader } from '@ngx-translate/core';
import { Observable, forkJoin } from 'rxjs';
import { LoadingHttpService } from 'varda-shared';
import { filter } from 'rxjs/operators';
import { SupportedLanguages } from 'projects/varda-shared/src/lib/dto/supported-languages.enum';
import { AngularTranslateDTO, TranslationDTO } from 'projects/varda-shared/src/lib/dto/translation-dto';
import { VardaApiServiceInterface } from 'projects/varda-shared/src/lib/dto/vardaApiService.interface';


export class VirkailijaTranslateLoader implements TranslateLoader {
  translationCategory: string;
  localizationApi: string;

  constructor(private http: LoadingHttpService, private appApi: VardaApiServiceInterface) {
    this.translationCategory = appApi.getTranslationCategory();
    this.localizationApi = appApi.getLocalizationApi();
  }
  getTranslation(lang: SupportedLanguages, attemptNr = 0): Observable<AngularTranslateDTO> {
    return new Observable(preparedTranslation => {
      this.http.getApiKey().pipe(filter(Boolean)).subscribe(() =>
        this.fetchJson(lang).subscribe(angularTranslation =>
          this.fetchTranslations(lang).subscribe(translation => {
            preparedTranslation.next(this.handleTranslations(angularTranslation, translation, lang));
            preparedTranslation.complete();
          }, () => {
            if (attemptNr < 2) {
              setTimeout(() => this.getTranslation(lang, attemptNr++), 200);
            } else {
              console.error('Failed to load translations');
              preparedTranslation.next({});
              preparedTranslation.complete();
            }
          })
        )
      );
    });
  }


  fetchTranslations(lang: SupportedLanguages): Observable<Array<TranslationDTO>> {
    return this.http.get(`${this.localizationApi}/?category=${this.translationCategory}&locale=${lang}`);
  }

  fetchJson(lang: SupportedLanguages): Observable<AngularTranslateDTO> {
    return this.http.get(`assets/i18n/${lang}.json`);
  }

  handleTranslations(existingTranslations: AngularTranslateDTO, translations: Array<TranslationDTO>, lang: SupportedLanguages): AngularTranslateDTO {
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

    return i18nTranslations;
  }

}
