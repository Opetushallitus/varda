import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { CodeDTO, KoodistoDTO, KoodistoEnum, KoodistoSortBy } from './dto/koodisto-models';
import { LoadingHttpService } from './loading-http.service';

@Injectable({
  providedIn: 'root'
})
export class VardaKoodistoService {
  private static primaryLanguages = ['FI', 'SV', 'SEPO', 'RU', 'ET', 'EN', 'AR', 'SO', 'DE', 'FR'];
  private vardaApiUrl: string;
  private koodistot$ = new BehaviorSubject<Array<KoodistoDTO>>(null);

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

  initKoodistot(vardaApiUrl: string, lang: string) {
    this.vardaApiUrl = vardaApiUrl;
    this.getKoodistot(lang).subscribe(koodistoJSON => this.koodistot$.next(koodistoJSON));
  }

  private getKoodistot(lang: string): Observable<Array<KoodistoDTO>> {
    return this.http.get(`${this.vardaApiUrl}/api/julkinen/koodistot/v1/?lang=${lang}`);
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
}
