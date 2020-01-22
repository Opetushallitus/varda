import { Injectable } from '@angular/core';
import { VardaApiService } from './varda-api.service';
import { Observable } from 'rxjs';
import { TranslateService, LangChangeEvent } from '@ngx-translate/core';
import { VardaDateService } from '../../varda-main/services/varda-date.service';
import * as moment from 'moment';


@Injectable({
  providedIn: 'root'
})
export class VardaKuntakoodistoService {

  kuntakoodistoOptions: Array<any> = [];
  currentLang: string;

  constructor(private vardaApiService: VardaApiService,
    private translateService: TranslateService,
    private vardaDateService: VardaDateService) {
    this.currentLang = this.translateService.currentLang;
    this.translateService.onLangChange.subscribe((event: LangChangeEvent) => {
      this.currentLang = event.lang;
      this.sortKuntakoodistoOptions();
    });
  }

  initKuntakoodisto(): Observable<any> {
    return new Observable((observer) => {
        this.vardaApiService.getKuntakoodistoOptions().subscribe((data) => {
            this.kuntakoodistoOptions = data;
            this.sortKuntakoodistoOptions();
            this.excludeOutDatedKuntakoodistoOptions();
            observer.next(true);
            observer.complete();
        }, () => observer.error({kuntakoodistoUnavailable: true}));
    });
  }

  getKuntakoodistoOptions(): Array<any> {
    return this.kuntakoodistoOptions;
  }

  getKuntakoodistoOptionByKuntakoodi(searchVal: string): any {
    const kuntakoodiMatch = this.kuntakoodistoOptions.find((langOption) => {
      return langOption.koodiArvo.toUpperCase() === searchVal.toUpperCase();
    });
    return kuntakoodiMatch;
  }

  getKuntaKoodistoOptionMetadataByLang(kuntaKoodistoOptionMetadata: any, language: string): any {
    const metadata = kuntaKoodistoOptionMetadata.find((metadataObj) => {
      return metadataObj.kieli.toUpperCase() === language.toUpperCase();
    });
    return metadata;
  }

  sortKuntakoodistoOptions(): Array<any> {
    this.kuntakoodistoOptions.sort((a: any, b: any) => {
      const metadataFiA = this.getKuntaKoodistoOptionMetadataByLang(
        a.metadata, this.currentLang);
      const metadataFiB = this.getKuntaKoodistoOptionMetadataByLang(
        b.metadata, this.currentLang);

      const nameA = metadataFiA.nimi.toUpperCase();
      const nameB = metadataFiB.nimi.toUpperCase();

      if (nameA < nameB) {
        return -1;
      }
      if (nameA > nameB) {
        return 1;
      }
      return 0;
    });

    return this.kuntakoodistoOptions;
  }

  excludeOutDatedKuntakoodistoOptions(): Array<any> {
    try {
      this.kuntakoodistoOptions = this.kuntakoodistoOptions.filter((kuntakoodiItem) => {
        const voimassaLoppuPvm = kuntakoodiItem.voimassaLoppuPvm;
        if (!voimassaLoppuPvm) {
          return true;
        }

        const today = moment();
        const voimassaLoppuPvmUIDate = this.vardaDateService.vardaDateToUIDate(voimassaLoppuPvm);
        const voimassaLoppuPvmMoment = this.vardaDateService.uiDateToMoment(voimassaLoppuPvmUIDate);
        const todayIsBeforeVoimassaLoppuPvm = this.vardaDateService.date1IsBeforeDate2(today, voimassaLoppuPvmMoment);
        return todayIsBeforeVoimassaLoppuPvm ? true : false;
      });
      return this.kuntakoodistoOptions;
    } catch (e) {
      console.log(e);
    }
  }
}
