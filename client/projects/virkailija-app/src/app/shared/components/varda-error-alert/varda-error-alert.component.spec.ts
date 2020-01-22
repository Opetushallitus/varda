import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { VardaErrorAlertComponent } from './varda-error-alert.component';
import {TranslatePipe, TranslateService} from '@ngx-translate/core';
import {TranslateServiceStub} from '../../../core/services/varda-maksun-peruste-koodisto-service.service.spec';
import {EMPTY} from 'rxjs';

describe('VardaErrorAlertComponent', () => {
  let component: VardaErrorAlertComponent;
  let fixture: ComponentFixture<VardaErrorAlertComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [
        VardaErrorAlertComponent,
        TranslatePipe,
      ],
      providers: [
        { provide: TranslateService, useClass: TranslateServiceStub},
      ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(VardaErrorAlertComponent);
    component = fixture.componentInstance;
    component.errorMessageKey$ = EMPTY;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
