import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { HuoltajaUnauthorisedComponent } from './huoltaja-unauthorised.component';

describe('HuoltajaUnauthorisedComponent', () => {
  let component: HuoltajaUnauthorisedComponent;
  let fixture: ComponentFixture<HuoltajaUnauthorisedComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ HuoltajaUnauthorisedComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(HuoltajaUnauthorisedComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
