import { TestBed, async } from '@angular/core/testing';
import { AppComponent } from './app.component';
import { TranslateService } from '@ngx-translate/core';
import { VardaSharedModule, LoadingHttpService } from 'varda-shared';
import { RouterTestingModule } from '@angular/router/testing';

describe('AppComponent', () => {
  let loadingHttpService: LoadingHttpService;

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
        { provide: LoadingHttpService, useValue: { isLoading: () => { } } },
        { provide: TranslateService, useValue: { use: () => { }, setDefaultLang: () => { } } }
      ]
    }).compileComponents();

    loadingHttpService = TestBed.inject<LoadingHttpService>(LoadingHttpService);
  }));

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.debugElement.componentInstance;
    expect(app).toBeTruthy();
  });

  it(`should have as title 'huoltaja-app'`, () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.debugElement.componentInstance;
    expect(app.title).toEqual('huoltaja-app');
  });
});
