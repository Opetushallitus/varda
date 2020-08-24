import { Injectable } from '@angular/core';
import { Observable, BehaviorSubject } from 'rxjs';
import { TranslateService, LangChangeEvent } from '@ngx-translate/core';
import { KoodistoDTO, KoodistoEnum, CodeDTO, KoodistoSortBy } from './dto/koodisto-models';
import { LoadingHttpService } from './loading-http.service';

@Injectable({
  providedIn: 'root'
})
export class VardaKoodistoService {
  private vardaApiUrl: string;
  private koodistot$ = new BehaviorSubject<Array<KoodistoDTO>>(null);

  constructor(
    private http: LoadingHttpService,
    private translateService: TranslateService,
  ) {

  }

  initKoodistot(vardaApiUrl: string) {
    this.vardaApiUrl = vardaApiUrl;
    this.getKoodistot(this.translateService.currentLang).subscribe(koodistoJSON => this.koodistot$.next(koodistoJSON));

    this.translateService.onLangChange.subscribe((event: LangChangeEvent) => {
      this.getKoodistot(event.lang).subscribe(koodistoJSON => this.koodistot$.next(koodistoJSON));
    });
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
