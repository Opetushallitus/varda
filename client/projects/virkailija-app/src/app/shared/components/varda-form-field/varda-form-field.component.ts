import { Component, Input, OnChanges, Output, EventEmitter, ContentChildren, QueryList, AfterContentInit, ElementRef, ContentChild, ViewChild, OnDestroy } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { VardaField, } from '../../../utilities/models';
import { MatRadioGroup, MatRadioButton } from '@angular/material/radio';
import { VardaDatepickerComponent } from '../varda-datepicker/varda-datepicker.component';
import { Subscription, Subject, Observable, fromEvent } from 'rxjs';

export interface FormFieldErrorMap {
  key: string;
  value: string;
}

export enum VardaFormFieldType {
  text = 'text',
  number = 'number',
  select = 'select',
  datepicker = 'datepicker'
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
  @ContentChildren(MatRadioButton) radioButtons: MatRadioButton[];
  @ContentChild(VardaDatepickerComponent) datePicker: VardaDatepickerComponent;

  labelId: string;
  formControl: FormControl;
  focusStatus$ = new Subject<boolean>();
  vardaFormFieldTypes = VardaFormFieldType;
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
    this.labelId = `${this.name}Label_${Math.random().toString(36)}`;

    if (this.form) {
      this.formControl = <FormControl>this.form.get(this.name);
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
      this.subscriptions.push(this.datePicker.focusObservable().subscribe(value => this.focusStatus$.next(value)));
    }

    this.childComponents.filter(childEl => childEl.nativeElement).forEach(childEl => {
      childEl.nativeElement.name = childEl.nativeElement.name || this.name;
      childEl.nativeElement.placeholder = this.placeholder;
      childEl.nativeElement.setAttribute('aria-labelledby', this.labelId);
      this.subscriptions.push(fromEvent(childEl.nativeElement, 'focus').subscribe(() => this.focusStatus$.next(true)));
      this.subscriptions.push(fromEvent(childEl.nativeElement, 'blur').subscribe(() => this.focusStatus$.next(false)));
    });
  }
}

