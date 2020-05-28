import { TestBed, async } from '@angular/core/testing';
import { AppComponent } from './app.component';
import { TranslateService } from '@ngx-translate/core';
import { EMPTY } from 'rxjs';
import { LoadingHttpService } from 'varda-shared';
import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { RouterTestingModule } from '@angular/router/testing';

@Component({
  selector: 'app-public-header',
  template: ''
})
class MockPublicHeaderComponent {
}

describe('AppComponent', () => {
  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [
        RouterTestingModule,
      ],
      declarations: [
        AppComponent,
        MockPublicHeaderComponent,
      ],
      providers: [
        {
          provide: LoadingHttpService,
          useValue: { isLoading: () => { } }
        },
        {
          provide: Router,
          useValue: { events: EMPTY, navigate: () => { }, routerState: {} }
        },
        {
          provide: TranslateService,
          useValue: { use: () => { }, getBrowserLang: () => { }, setDefaultLang: () => { }, get: () => EMPTY }
        },
      ]
    }).compileComponents();
  }));

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
