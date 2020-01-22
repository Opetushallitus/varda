import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { VardaDeleteButtonComponent } from './varda-delete-button.component';

describe('VardaDeleteButtonComponent', () => {
  let component: VardaDeleteButtonComponent;
  let fixture: ComponentFixture<VardaDeleteButtonComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ VardaDeleteButtonComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(VardaDeleteButtonComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
