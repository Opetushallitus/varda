import { TestBed, async } from '@angular/core/testing';
import { AppComponent } from './app.component';
import { TranslateService } from '@ngx-translate/core';
import { VardaSharedModule, LoadingHttpService, LoginService } from 'varda-shared';
import { RouterTestingModule } from '@angular/router/testing';
import { EMPTY, Observable, of } from 'rxjs';
import { MatLegacySnackBar as MatSnackBar } from '@angular/material/legacy-snack-bar';

describe('AppComponent', () => {
  let loadingHttpService: LoadingHttpService;
  let loadingHttpServiceSpy;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        VardaSharedModule,
        RouterTestingModule
      ],
      declarations: [
        AppComponent
      ],
      providers: [
        { provide: MatSnackBar, useValue: EMPTY },
        { provide: LoginService, useValue: { getCurrentUser: () => of(null), setUsername: () => { }, initBroadcastChannel: () => { } } },
        { provide: LoadingHttpService, useValue: { isLoading: () => { }, isLoadingWithDebounce: () => { } } },
        { provide: TranslateService, useValue: { use: () => { }, setDefaultLang: () => { }, getBrowserLang: () => { }, stream: () => EMPTY } }
      ]
    }).compileComponents();

    loadingHttpService = TestBed.inject<LoadingHttpService>(LoadingHttpService);
    loadingHttpServiceSpy = spyOn(loadingHttpService, 'isLoading').and.returnValue(new Observable());
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.debugElement.componentInstance;
    expect(app).toBeTruthy();
  });
});
