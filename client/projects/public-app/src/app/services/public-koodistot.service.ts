import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { PublicApiService } from './public-api.service';
import { LangChangeEvent, TranslateService } from '@ngx-translate/core';
import { KoodistoDto } from '../models/koodisto-dto';

@Injectable({
  providedIn: 'root'
})
export class PublicKoodistotService {
  private currentLang: string;
  private koodistotObject: Object = {};
  private koodistot: BehaviorSubject<Array<KoodistoDto>> = new BehaviorSubject<Array<KoodistoDto>>([]);
  private koodistoIndexMap: Object = {};
  private koodistoNames: BehaviorSubject<Array<string>> = new BehaviorSubject<Array<string>>([]);
  private selectedKoodisto: BehaviorSubject<string> = new BehaviorSubject<string>('');

  constructor(private publicApiService: PublicApiService, private translateService: TranslateService) {
    this.currentLang = this.determineLanguage(this.translateService.currentLang);
    this.getKoodistotFromObjectOrApi(this.currentLang);
    this.translateService.onLangChange.subscribe((params: LangChangeEvent) => {
      const newLang = this.determineLanguage(params.lang);
      if (newLang !== this.currentLang) {
        this.currentLang = newLang;
        this.getKoodistotFromObjectOrApi(this.currentLang);
      }
    });
  }

  private getKoodistotFromObjectOrApi(lang: string) {
    if (this.koodistotObject.hasOwnProperty(lang)) {
      // Don't refetch koodistot
      this.koodistot.next(this.koodistotObject[lang]);
    } else {
      // Get koodistot for this language for the first time
      this.publicApiService.getKoodistot({'lang': lang}).subscribe(data => {
        const koodistoNamesList = [];

        data.forEach((value, index) => {
          this.koodistoIndexMap[value.name] = index;
          koodistoNamesList.push(value.name);
        });

        this.koodistoNames.next(koodistoNamesList);
        this.koodistotObject[lang] = data;
        this.koodistot.next(data);
      }, e => {
        // TODO: Handle 429 error (remove special handling from http.service:54)
      });
    }
  }

  getKoodistot(): BehaviorSubject<Array<KoodistoDto>> {
    return this.koodistot;
  }

  getKoodistoNames(): BehaviorSubject<Array<string>> {
    return this.koodistoNames;
  }

  getKoodistoIndex(name: string): number {
    if (this.koodistoIndexMap.hasOwnProperty(name)) {
      return this.koodistoIndexMap[name];
    } else {
      return -1;
    }
  }

  updateSelectedKoodisto(name: string) {
    this.selectedKoodisto.next(name);
  }

  getSelectedKoodisto(): BehaviorSubject<string> {
    return this.selectedKoodisto;
  }

  searchCodes(searchTerm: string): Array<KoodistoDto> {
    const results = [];
    searchTerm = searchTerm.toLowerCase();

    this.koodistot.value.forEach(koodisto => {
      const temp_results = koodisto.codes.filter(code => code.code_value.toLowerCase().includes(searchTerm) ||
        code.name.toLowerCase().includes(searchTerm) ||
        code.description.toLowerCase().includes(searchTerm));

      if (temp_results.length > 0) {
        koodisto.codes = temp_results;
        results.push(koodisto);
      }
    });

    return results;
  }

  private determineLanguage(lang: string) {
    lang = lang.toUpperCase();
    if (!['FI', 'SV', 'EN'].includes(lang)) {
      lang = 'FI';
    }
    return lang;
  }
}
