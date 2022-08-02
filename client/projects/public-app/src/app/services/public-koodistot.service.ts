import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { PublicApiService } from './public-api.service';
import { TranslateService } from '@ngx-translate/core';
import { KoodistoDto } from '../models/koodisto-dto';
import { VardaKoodistoService } from 'varda-shared';
import { filter } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class PublicKoodistotService {
  private koodistot: BehaviorSubject<Array<KoodistoDto>> = new BehaviorSubject<Array<KoodistoDto>>([]);
  private koodistoIndexMap: Record<string, number> = {};
  private koodistoNames: BehaviorSubject<Array<string>> = new BehaviorSubject<Array<string>>([]);
  private selectedKoodisto: BehaviorSubject<string> = new BehaviorSubject<string>('');

  constructor(
    private publicApiService: PublicApiService,
    private translateService: TranslateService,
    private koodistoService: VardaKoodistoService,
  ) {
    this.koodistoService.getKoodistot().pipe(filter(Boolean)).subscribe(data => {
      const koodistoNamesList = [];

      data.forEach((value, index) => {
        this.koodistoIndexMap[value.name] = index;
        koodistoNamesList.push(value.name);
      });

      this.koodistoNames.next(koodistoNamesList);
      this.koodistot.next(data);
    });
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
}
