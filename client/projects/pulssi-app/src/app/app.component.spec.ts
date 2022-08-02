import { TestBed } from '@angular/core/testing';
import { AppComponent } from './app.component';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { LoadingHttpService } from 'varda-shared';
import { Router } from '@angular/router';
import { EMPTY } from 'rxjs';
import { Component } from '@angular/core';

@Component({
  selector: 'app-header',
  template: ''
})
class MockHeaderComponent {
}

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        RouterTestingModule,
        TranslateModule.forRoot(),
      ],
      declarations: [
        AppComponent,
        MockHeaderComponent
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
          useValue: { use: () => { }, getBrowserLang: () => { }, setDefaultLang: () => { }, stream: () => EMPTY }
        },
      ]
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
