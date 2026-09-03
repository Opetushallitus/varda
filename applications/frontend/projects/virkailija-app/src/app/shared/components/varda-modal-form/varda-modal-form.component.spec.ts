import { ComponentFixture, TestBed } from '@angular/core/testing';

import { VardaModalFormComponent } from './varda-modal-form.component';
import {TranslateModule} from '@ngx-translate/core';

describe('VardaModalFormComponent', () => {
  let component: VardaModalFormComponent;
  let fixture: ComponentFixture<VardaModalFormComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [ VardaModalFormComponent ],
      imports: [TranslateModule.forRoot()]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(VardaModalFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
