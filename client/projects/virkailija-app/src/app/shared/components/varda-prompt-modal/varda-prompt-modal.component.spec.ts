import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { VardaPromptModalComponent } from './varda-prompt-modal.component';
import {VardaDeleteButtonComponent} from '../varda-delete-button/varda-delete-button.component';
import {TranslatePipe} from '../../../varda-main/components/varda-paos-management-container/varda-paos-management-container.component.spec';
import {Subject} from 'rxjs';

describe('VardaPromptModalComponent', () => {
  let component: VardaPromptModalComponent;
  let fixture: ComponentFixture<VardaPromptModalComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [
        VardaPromptModalComponent,
        VardaDeleteButtonComponent,
        TranslatePipe,
      ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(VardaPromptModalComponent);
    component = fixture.componentInstance;
    component.show$ = new Subject<boolean>();
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
