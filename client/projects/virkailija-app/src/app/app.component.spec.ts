import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { AppComponent } from './app.component';
import { TranslateService, LangChangeEvent } from '@ngx-translate/core';
import { AuthService } from './core/auth/auth.service';
import { VardaDomService } from './core/services/varda-dom.service';
import { EMPTY, Observable, of } from 'rxjs';
import { VardaApiService } from './core/services/varda-api.service';
import { CookieService } from 'ngx-cookie-service';
import { VardaVakajarjestajaService } from './core/services/varda-vakajarjestaja.service';
import { Router } from '@angular/router';
import { LoadingHttpService, VardaKoodistoService } from 'varda-shared';

describe('AppComponent', () => {
  let component: AppComponent;
  let fixture: ComponentFixture<AppComponent>;

  let vardaAuthService: AuthService;
  let loadingHttpService;
  let translateService: TranslateService;

  let loggedInUserAsiointikieliSetSpy, translateServiceUseSpy, loadingHttpServiceSpy;

  beforeEach(async(() => {
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
        { provide: TranslateService, useValue: { use: () => { }, getBrowserLang: () => { }, setDefaultLang: () => { }, get: () => EMPTY } },
        { provide: LoadingHttpService, useValue: { isLoading: () => { } } },
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

  it('Should set asiointikieli and pass to translateservice', () => {
    loggedInUserAsiointikieliSetSpy = spyOn(vardaAuthService, 'loggedInUserAsiointikieliSet').and.returnValue(of('sv'));
    vardaAuthService.setUserAsiointikieli('sv');
    expect(translateServiceUseSpy).toHaveBeenCalledWith('sv');
  });

  it('Should fallback to finnish asiointikieli and pass to translateservice', () => {
    loggedInUserAsiointikieliSetSpy = spyOn(vardaAuthService, 'loggedInUserAsiointikieliSet').and.returnValue(of('en'));
    vardaAuthService.setUserAsiointikieli('en');
    expect(translateServiceUseSpy).toHaveBeenCalledWith('fi');
  });

  it('Should fallback to finnish asiointikieli and pass to translateservice', () => {
    loggedInUserAsiointikieliSetSpy = spyOn(vardaAuthService, 'loggedInUserAsiointikieliSet').and.returnValue(of('asdfasdf'));
    vardaAuthService.setUserAsiointikieli('asdfasdf');
    expect(translateServiceUseSpy).toHaveBeenCalledWith('fi');
  });
});
