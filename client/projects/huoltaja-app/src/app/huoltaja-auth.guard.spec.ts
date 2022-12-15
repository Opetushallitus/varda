import { TestBed, inject } from '@angular/core/testing';

import { HuoltajaAuthGuard } from './huoltaja-auth.guard';
import {HttpClient} from '@angular/common/http';
import { CookieService } from 'ngx-cookie-service';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { MatLegacySnackBar as MatSnackBar } from '@angular/material/legacy-snack-bar';
import { EMPTY } from 'rxjs';

describe('HuoltajaAuthGuard', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        HuoltajaAuthGuard,
        { provide: MatSnackBar, useValue: EMPTY },
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
