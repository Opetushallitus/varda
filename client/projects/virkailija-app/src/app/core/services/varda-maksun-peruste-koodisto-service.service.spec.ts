import { TestBed } from '@angular/core/testing';

import { VardaMaksunPerusteKoodistoService } from './varda-maksun-peruste-koodisto.service';
import {VardaApiService} from './varda-api.service';
import {TranslateService} from '@ngx-translate/core';
import {of} from 'rxjs';

export class TranslateServiceStub {
  setDefaultLang(lang: string) { }
  use(lang: string) { }
  get onLangChange() { return of({lang: 'fi'}); }
}

describe('VardaMaksunPerusteKoodistoServiceService', () => {
  beforeEach(() => TestBed.configureTestingModule({
    providers: [
      {provide: VardaApiService, useValue: {}},
      { provide: TranslateService, useClass: TranslateServiceStub},
    ]
  }));

  it('should be created', () => {
    const service: VardaMaksunPerusteKoodistoService = TestBed.inject<VardaMaksunPerusteKoodistoService>(VardaMaksunPerusteKoodistoService);
    expect(service).toBeTruthy();
  });
});
