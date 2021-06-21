import { Component, Input, ContentChildren, QueryList, AfterContentInit, ElementRef, ContentChild, ViewChild, OnDestroy } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { VardaField, } from '../../../utilities/models';
import { MatRadioGroup, MatRadioButton } from '@angular/material/radio';
import { VardaDatepickerComponent } from '../varda-datepicker/varda-datepicker.component';
import { Subscription, Subject, Observable, fromEvent } from 'rxjs';
import { MatSelect } from '@angular/material/select';

export interface FormFieldErrorMap {
  key: string;
  value: string;
}

@Component({
  selector: 'app-varda-form-field',
  templateUrl: './varda-form-field.component.html',
  styleUrls: ['./varda-form-field.component.css']
})
export class VardaFormFieldComponent implements AfterContentInit, OnDestroy {
  @Input() label: string;
  @Input() name: string;
  @Input() errorText: string;
  @Input() errorMap: Array<FormFieldErrorMap>;
  @Input() error: boolean;
  @Input() placeholder: string;
  @Input() instructionText: string;
  @Input() hilight: boolean;
  @Input() readOnly: boolean;
  @Input() required: boolean;
  @Input() form: FormGroup;

  @ContentChildren('fieldItem') childComponents: QueryList<ElementRef>;
  @ViewChild('formField') formField: ElementRef;
  @ContentChild(MatRadioGroup) radioGroup: MatRadioGroup;
  @ContentChild(MatSelect) select: MatSelect;
  @ContentChildren(MatRadioButton) radioButtons: MatRadioButton[];
  @ContentChild(VardaDatepickerComponent) datePicker: VardaDatepickerComponent;

  labelId: string;
  errorRef: string;
  instructionRef: string;
  formControl: FormControl;
  focusStatus$ = new Subject<boolean>();
  showInstructionText: boolean;
  isRequired: boolean;
  private subscriptions: Subscription[] = [];

  constructor() {
    this.showInstructionText = false;
  }

  onBlur(field: VardaField): void {
    this.showInstructionText = false;
  }

  onFocus(field: VardaField): void {
    this.showInstructionText = true;
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription?.unsubscribe());
  }

  ngAfterContentInit() {
    this.placeholder = this.placeholder || this.label;
    this.labelId = `${this.name}-label-${Math.random().toString(36)}`;
    this.errorRef = `${this.name}-error`;
    this.instructionRef = `${this.name}-instruction`;

    if (this.form) {
      this.formControl = this.form.get(this.name) as FormControl;
      this.formControl.statusChanges.subscribe(change => {
        if (this.formControl.hasError('scrollTo')) {
          this.formField?.nativeElement.scrollIntoView({ behavior: 'smooth' });
        }
      });
    }

    if (this.radioGroup) {
      this.subscriptions.push(this.formControl.valueChanges.subscribe((change: Observable<boolean>) => {
        this.focusStatus$.next(true);
        setTimeout(() => this.focusStatus$.next(false), 2000);
      }));
    } else if (this.datePicker) {
      this.datePicker.attrName = this.datePicker.attrName || this.name;
      this.subscriptions.push(this.datePicker.focusObservable().subscribe(value => this.focusStatus$.next(value)));
    } else if (this.select) {
      this.subscriptions.push(
        this.select._openedStream.subscribe(() => this.focusStatus$.next(true)),
        this.select._closedStream.subscribe(() => this.focusStatus$.next(false)),
      );
    }

    this.childComponents.filter(childEl => childEl.nativeElement).forEach(childEl => {
      childEl.nativeElement.name = childEl.nativeElement.name || this.name;
      childEl.nativeElement.placeholder = this.placeholder;
      childEl.nativeElement.setAttribute('aria-labelledby', this.labelId);
      childEl.nativeElement.setAttribute('robot', this.name);
      this.subscriptions.push(fromEvent(childEl.nativeElement, 'focus').subscribe(() => this.focusStatus$.next(true)));
      this.subscriptions.push(fromEvent(childEl.nativeElement, 'blur').subscribe(() => this.focusStatus$.next(false)));
    });
  }
}

