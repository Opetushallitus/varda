import { TestBed, inject } from '@angular/core/testing';

import { HuoltajaAuthGuard } from './huoltaja-auth.guard';
import {HttpClient} from '@angular/common/http';
import { CookieService } from 'ngx-cookie-service';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';

describe('HuoltajaAuthGuard', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        HuoltajaAuthGuard,
        { provide: HttpClient, useValue: {} },
        { provide: CookieService, useValue: {} },
        { provide: Router, useValue: {} },
        { provide: TranslateService, useValue: {} }
      ]
    });
  });

  it('should ...', inject([HuoltajaAuthGuard], (guard: HuoltajaAuthGuard) => {
    expect(guard).toBeTruthy();
  }));
});
