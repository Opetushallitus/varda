import { TranslateLoader } from '@ngx-translate/core';
import { Observable } from 'rxjs';
import { TranslationDTO, AngularTranslateDTO } from './dto/translation-dto';
import { LoadingHttpService } from './loading-http.service';
import { SupportedLanguages } from './dto/supported-languages.enum';
import { VardaApiServiceInterface } from './dto/vardaApiService.interface';
import { HttpHeaders } from '@angular/common/http';


export class VardaTranslateLoader implements TranslateLoader {
  translationCategory: string;
  localizationApi: string;

  constructor(private http: LoadingHttpService, private appApi: VardaApiServiceInterface) {
    this.translationCategory = appApi.getTranslationCategory();
    this.localizationApi = appApi.getLocalizationApi();


  }
  getTranslation(lang: SupportedLanguages, attemptNr = 0): Observable<AngularTranslateDTO> {
    return new Observable(preparedTranslation => {
      this.fetchTranslations(lang).subscribe(translation => {
        preparedTranslation.next(this.handleTranslations(translation, lang));
        preparedTranslation.complete();
      }, () => {
        if (attemptNr < 2) {
          setTimeout(() => this.getTranslation(lang, attemptNr++), 200);
        } else {
          console.error('Failed to load translations');
          preparedTranslation.next({});
          preparedTranslation.complete();
        }
      });
    });
  }


  fetchTranslations(lang: SupportedLanguages): Observable<Array<TranslationDTO>> {
    return this.http.get(`${this.localizationApi}/?category=${this.translationCategory}&locale=${lang}`, null, new HttpHeaders());
  }


  handleTranslations(translations: Array<TranslationDTO>, lang: SupportedLanguages): AngularTranslateDTO {
    const translationEnum = this.appApi.getTranslationEnum();
    const i18nTranslations = {};
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

    return i18nTranslations;
  }
}
