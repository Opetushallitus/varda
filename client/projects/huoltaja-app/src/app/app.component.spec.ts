import { TestBed, async } from '@angular/core/testing';
import { AppComponent } from './app.component';
import { TranslateService } from '@ngx-translate/core';
import { VardaSharedModule, LoadingHttpService, LoginService, HttpService } from 'varda-shared';
import { RouterTestingModule } from '@angular/router/testing';
import { Observable } from 'rxjs/internal/Observable';
import { EMPTY } from 'rxjs';

describe('AppComponent', () => {
  let loadingHttpService: LoadingHttpService;
  let loadingHttpServiceSpy;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [
        VardaSharedModule,
        RouterTestingModule
      ],
      declarations: [
        AppComponent
      ],
      providers: [
        { provide: LoginService, useValue: EMPTY },
        { provide: LoadingHttpService, useValue: { isLoading: () => { } } },
        { provide: TranslateService, useValue: { use: () => { }, setDefaultLang: () => { }, getBrowserLang: () => { } } }
      ]
    }).compileComponents();

    loadingHttpService = TestBed.inject<LoadingHttpService>(LoadingHttpService);
    loadingHttpServiceSpy = spyOn(loadingHttpService, 'isLoading').and.returnValue(new Observable());
  }));

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.debugElement.componentInstance;
    expect(app).toBeTruthy();
  });
});
