import { Injectable } from '@angular/core';
import { VardaApiService } from './varda-api.service';
import { Observable } from 'rxjs';
import { TranslateService, LangChangeEvent } from '@ngx-translate/core';
import * as moment from 'moment';
import { VardaDateService } from '../../varda-main/services/varda-date.service';

@Injectable({
  providedIn: 'root'
})
export class VardaKielikoodistoService {

  kielikoodistoOptions: Array<any> = [];
  primaryLanguages: Array<any>;
  currentLang: string;

  constructor(private vardaApiService: VardaApiService, private translateService: TranslateService,
    private vardaDateService: VardaDateService) {
    this.primaryLanguages = ['FI', 'SV', 'SEPO', 'RU', 'ET', 'EN', 'AR', 'SO', 'DE', 'FR'];
    this.currentLang = this.translateService.currentLang;
    this.translateService.onLangChange.subscribe((event: LangChangeEvent) => {
      this.currentLang = event.lang;
      this.sortKielikoodistoOptions();
    });
  }

  initKielikoodisto(): Observable<any> {
    return new Observable((observer) => {
      this.vardaApiService.getKielikoodistoOptions().subscribe((data) => {
        this.kielikoodistoOptions = data;
        this.sortKielikoodistoOptions();
        this.excludeOutDatedKielikoodistoOptions();
        observer.next(true);
        observer.complete();
      }, () => observer.error({ kielikoodistoUnavailable: true }));
    });
  }

  getKielikoodistoOptions(): Array<any> {
    return this.kielikoodistoOptions;
  }

  getKielikoodistoOptionByLangAbbreviation(searchVal: string): any {
    const languageMatch = this.kielikoodistoOptions.find((langOption) => {
      return langOption.koodiArvo.toUpperCase() === searchVal.toUpperCase();
    });
    return languageMatch;
  }

  getKielikoodistoOptionIndexByLangAbbreviation(searchVal: string): any {
    const languageMatch = this.kielikoodistoOptions.findIndex((langOption) => {
      if (!langOption) {
        return false;
      }
      return langOption.koodiArvo.toUpperCase() === searchVal.toUpperCase();
    });
    return languageMatch;
  }

  getKielikoodistoOptionMetadataByLang(kielikoodistoOptionMetadata: any, language: string): any {
    let metadata = kielikoodistoOptionMetadata.find((metadataObj) => {
      return metadataObj.kieli.toUpperCase() === language.toUpperCase();
    });

    if (!metadata) {
      metadata = kielikoodistoOptionMetadata.find((metadataObj) => {
        return metadataObj.kieli.toUpperCase() === 'FI';
      });
    }

    return metadata;
  }

  sortKielikoodistoOptions(): Array<any> {
    this.kielikoodistoOptions.sort(this.sortByLanguageName.bind(this));

    for (let x = this.primaryLanguages.length - 1; x >= 0; x--) {
      try {
        const kielikoodiObjIndex = this.getKielikoodistoOptionIndexByLangAbbreviation(
          this.primaryLanguages[x]);
        const kielikoodiObj = this.kielikoodistoOptions[kielikoodiObjIndex];
        this.kielikoodistoOptions.splice(kielikoodiObjIndex, 1);
        this.kielikoodistoOptions.unshift(kielikoodiObj);
      } catch (e) {
        console.log(e);
      }
    }

    return this.kielikoodistoOptions;
  }

  sortByLanguageName(a: any, b: any): number {
    try {
      const metadataA = this.getKielikoodistoOptionMetadataByLang(
        a.metadata, this.currentLang);
      const metadataB = this.getKielikoodistoOptionMetadataByLang(
        b.metadata, this.currentLang);

      if (!metadataA) {
        console.log(a);
      }

      if (!metadataB) {
        console.log(b);
      }

      const nameA = metadataA.nimi.toUpperCase();
      const nameB = metadataB.nimi.toUpperCase();

      if (nameA < nameB) {
        return -1;
      }
      if (nameA > nameB) {
        return 1;
      }
      return 0;
    } catch (e) {
      console.log(e);
    }
  }

  excludeOutDatedKielikoodistoOptions(): Array<any> {
    try {
      this.kielikoodistoOptions = this.kielikoodistoOptions.filter((kielikoodiItem) => {
        const voimassaLoppuPvm = kielikoodiItem.voimassaLoppuPvm;
        if (!voimassaLoppuPvm) {
          return true;
        }

        const today = moment(new Date());
        const voimassaLoppuPvmUIDate = this.vardaDateService.vardaDateToUIDate(voimassaLoppuPvm);
        const voimassaLoppuPvmMoment = this.vardaDateService.uiDateToMoment(voimassaLoppuPvmUIDate);
        const todayIsBeforeVoimassaLoppuPvm = this.vardaDateService.date1IsBeforeDate2(today, voimassaLoppuPvmMoment);
        return todayIsBeforeVoimassaLoppuPvm ? true : false;
      });
      return this.kielikoodistoOptions;
    } catch (e) {
      console.log(e);
    }
  }
}
