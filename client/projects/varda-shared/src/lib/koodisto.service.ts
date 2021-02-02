import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { CodeDTO, KoodistoDTO, KoodistoEnum, KoodistoSortBy } from './models/koodisto-models';
import { LoadingHttpService } from './loading-http.service';
import { HttpHeaders } from '@angular/common/http';
import { SupportedLanguage } from './models/translation-dto';

interface KoodistoCache {
  timestamp: number;
  language: SupportedLanguage;
  koodistot: Array<KoodistoDTO>;
}

@Injectable({
  providedIn: 'root'
})
export class VardaKoodistoService {
  private static primaryLanguages = ['FI', 'SV', 'SEPO', 'RU', 'ET', 'EN', 'AR', 'SO', 'DE', 'FR'];
  private vardaApiUrl: string;
  private koodistot$ = new BehaviorSubject<Array<KoodistoDTO>>(null);
  private koodistoCache = 'varda.koodistoCache';

  constructor(
    private http: LoadingHttpService
  ) { }

  static sortKieliKoodistoByPrimaryLanguages(koodisto: KoodistoDTO) {
    koodisto.codes = koodisto.codes.sort((a, b) => {
      const primaryIndexOfA = VardaKoodistoService.primaryLanguages.indexOf(a.code_value.toUpperCase());
      const primaryIndexOfB = VardaKoodistoService.primaryLanguages.indexOf(b.code_value.toUpperCase());
      const isAPrimaryLanguage = primaryIndexOfA !== -1;
      const isBPrimaryLanguage = primaryIndexOfB !== -1;
      if (!isAPrimaryLanguage && !isBPrimaryLanguage) {
        return a.code_value.localeCompare(b.code_value);
      } else if (isAPrimaryLanguage && !isBPrimaryLanguage) {
        return -1;
      } else if (!isAPrimaryLanguage && isBPrimaryLanguage) {
        return 1;
      } else {
        return primaryIndexOfA > primaryIndexOfB ? 1 : -1;
      }
    });
  }

  static getNumberOfPrimaryLanguages(): number {
    return VardaKoodistoService.primaryLanguages.length;
  }

  static mapCodesToFormOptions(koodisto: KoodistoDTO) {
    return koodisto.codes.map(code => {
      return {
        code: koodisto.name === KoodistoEnum.kieli ? code.code_value.toUpperCase() : code.code_value.toLowerCase(),
        displayName: {
          displayNameFi: code.name,
          displayNameSv: code.name
        }
      };
    });
  }

  static updateOptionsIfFound(fields, key, koodisto) {
    const fieldResult = fields.find(field => {
      return field.key === key;
    });

    if (!fieldResult) {
      console.error(`Form JSON file has been edited, ${key} not found`);
      return;
    }

    fieldResult.options = VardaKoodistoService.mapCodesToFormOptions(koodisto);
  }

  private getKoodistot(lang: SupportedLanguage): Observable<Array<KoodistoDTO>> {
    return this.http.get(`${this.vardaApiUrl}/api/julkinen/v1/koodistot/?lang=${lang}`, null, new HttpHeaders());
  }

  initKoodistot(vardaApiUrl: string, lang: SupportedLanguage) {
    this.vardaApiUrl = vardaApiUrl;
    this.checkCache(lang);
  }

  getKoodisto(koodistoNimi: KoodistoEnum, sortBy?: KoodistoSortBy): Observable<KoodistoDTO> {
    if (!this.vardaApiUrl) {
      return this.ErrorIfNotInitiated();
    }

    return new Observable(koodistoObs => {
      this.koodistot$.subscribe(koodistot => {
        if (koodistot) {
          // needs to be copied object so sub-functions wont modify the original
          const foundKoodisto = { ...koodistot.find(koodisto => koodistoNimi.toLocaleUpperCase() === koodisto.name.toLocaleUpperCase()) };

          if (sortBy) {
            foundKoodisto.codes.sort((a, b) => a[sortBy].localeCompare(b[sortBy]));
          }

          koodistoObs.next(foundKoodisto);
          koodistoObs.complete();
        }
      });
    });
  }

  getCodeValueFromKoodisto(koodistoNimi: KoodistoEnum, codeValue: string): Observable<CodeDTO> {
    if (!this.vardaApiUrl) {
      return this.ErrorIfNotInitiated();
    }

    return new Observable(koodistoObs => {
      this.koodistot$.subscribe(koodistot => {
        if (koodistot) {
          const foundKoodisto = koodistot.find(koodisto => koodistoNimi.toLocaleUpperCase() === koodisto.name.toLocaleUpperCase());
          const foundValue = foundKoodisto?.codes.find(code => codeValue.toLocaleUpperCase() === code.code_value.toLocaleUpperCase());
          koodistoObs.next(foundValue);
          koodistoObs.complete();
        }
      });
    });
  }

  ErrorIfNotInitiated(): Observable<any> {
    return new Observable(obs => {
      obs.error('Koodisto has not been initiated');
    });
  }

  checkCache(lang: SupportedLanguage) {
    const existingCache: KoodistoCache = JSON.parse(localStorage.getItem(this.koodistoCache));
    if (Date.now() - existingCache?.timestamp < 300000 && existingCache.language === lang) {
      return this.koodistot$.next(existingCache.koodistot);
    } else {
      this.getKoodistot(lang).subscribe({
        next: koodistoJSON => this.saveCache(koodistoJSON, lang),
        error: err => {
          if (existingCache) {
            this.koodistot$.next(existingCache.koodistot);
          } else {
            console.error(err.message);
          }
        }
      });
    }
  }

  saveCache(koodistoJSON: Array<KoodistoDTO>, lang: SupportedLanguage) {
    this.koodistot$.next(koodistoJSON);
    localStorage.setItem(this.koodistoCache, JSON.stringify({ timestamp: Date.now(), koodistot: koodistoJSON, language: lang }));
  }

}
