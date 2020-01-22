import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { VardaIconComponent } from './varda-icon.component';

describe('VardaIconComponent', () => {
  let component: VardaIconComponent;
  let fixture: ComponentFixture<VardaIconComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ VardaIconComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(VardaIconComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
