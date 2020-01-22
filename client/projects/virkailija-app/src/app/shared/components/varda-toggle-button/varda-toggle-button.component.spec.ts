import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { VardaToggleButtonComponent } from './varda-toggle-button.component';
import {TranslatePipe} from '../../../varda-main/components/varda-paos-management-container/varda-paos-management-container.component.spec';

describe('VardaToggleButtonComponent', () => {
  let component: VardaToggleButtonComponent;
  let fixture: ComponentFixture<VardaToggleButtonComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [
        VardaToggleButtonComponent,
        TranslatePipe,
      ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(VardaToggleButtonComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
