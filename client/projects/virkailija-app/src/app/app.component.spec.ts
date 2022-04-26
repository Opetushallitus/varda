import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { AppComponent } from './app.component';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from './core/auth/auth.service';
import { VardaDomService } from './core/services/varda-dom.service';
import { EMPTY, Observable, of } from 'rxjs';
import { VardaApiService } from './core/services/varda-api.service';
import { CookieService } from 'ngx-cookie-service';
import { VardaVakajarjestajaService } from './core/services/varda-vakajarjestaja.service';
import { Router } from '@angular/router';
import { LoadingHttpService, LoginService, VardaKoodistoService } from 'varda-shared';

describe('AppComponent', () => {
  let component: AppComponent;
  let fixture: ComponentFixture<AppComponent>;

  let vardaAuthService: AuthService;
  let loadingHttpService;
  let translateService: TranslateService;

  let translateServiceUseSpy; let loadingHttpServiceSpy;

  beforeEach((() => {
    TestBed.configureTestingModule({
      declarations: [AppComponent],
      schemas: [NO_ERRORS_SCHEMA],
      providers: [
        AuthService,
        VardaVakajarjestajaService,
        VardaDomService,
        { provide: Router, useValue: { events: EMPTY, navigate: () => { }, routerState: {} } },
        { provide: CookieService, useValue: {} },
        { provide: VardaApiService, useValue: {} },
        { provide: LoginService, useValue: { getCurrentUser: () => of(null), setUsername: () => { }, initBroadcastChannel: () => { } } },
        { provide: TranslateService, useValue: { use: () => { }, getBrowserLang: () => { }, setDefaultLang: () => { }, get: () => EMPTY } },
        { provide: LoadingHttpService, useValue: { isLoading: () => { }, isLoadingWithDebounce: () => { } } },
        { provide: VardaKoodistoService, useValue: { initKoodistot: () => { } } },
      ]
    })
      .compileComponents();

    vardaAuthService = TestBed.inject<AuthService>(AuthService);
    loadingHttpService = TestBed.inject<LoadingHttpService>(LoadingHttpService);
    translateService = TestBed.inject<TranslateService>(TranslateService);

    translateServiceUseSpy = spyOn(translateService, 'use').and.returnValue(new Observable());
    loadingHttpServiceSpy = spyOn(loadingHttpService, 'isLoading').and.returnValue(new Observable());
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AppComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the app', () => {
    const app = fixture.debugElement.componentInstance;
    expect(app).toBeTruthy();
  });
});
