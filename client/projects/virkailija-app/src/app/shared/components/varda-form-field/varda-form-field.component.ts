import {
  Component,
  Input,
  ContentChildren,
  QueryList,
  ElementRef,
  ContentChild,
  ViewChild,
  OnDestroy,
  OnChanges,
  SimpleChanges,
  AfterViewInit,
  OnInit
} from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { MatRadioGroup, MatRadioButton } from '@angular/material/radio';
import { VardaDatepickerComponent } from '../varda-datepicker/varda-datepicker.component';
import { Subscription, Subject, Observable, fromEvent } from 'rxjs';
import { MatSelect, MatSelectChange } from '@angular/material/select';
import { Element } from '@angular/compiler';
import {
  VardaAutocompleteSelectorComponent
} from '../varda-autocomplete-selector/varda-autocomplete-selector.component';

export interface FormFieldErrorMap {
  key: string;
  value: string;
}

@Component({
  selector: 'app-varda-form-field',
  templateUrl: './varda-form-field.component.html',
  styleUrls: ['./varda-form-field.component.css']
})
export class VardaFormFieldComponent implements OnInit, AfterViewInit, OnChanges, OnDestroy {
  @Input() label: string;
  @Input() name: string;
  @Input() errorText: string;
  @Input() errorMap: Array<FormFieldErrorMap>;
  @Input() error: boolean;
  @Input() placeholder: string;
  @Input() instructionText: string;
  @Input() readOnly: boolean;
  @Input() required: boolean;
  @Input() form!: FormGroup;

  @ContentChildren('fieldItem', { descendants: true }) childComponents:
    QueryList<ElementRef | MatSelect | VardaAutocompleteSelectorComponent<any>>;
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

  private subscriptions: Array<Subscription> = [];

  constructor() {
    this.showInstructionText = false;
  }

  ngOnInit() {
    this.placeholder = this.placeholder || this.label;
    this.labelId = `${this.name}-label-${Math.random().toString(36)}`;
    this.errorRef = `${this.name}-error`;
    this.instructionRef = `${this.name}-instruction`;
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.form) {
      this.initialize();
    }
  }

  ngAfterViewInit() {
    setTimeout(() => this.initialize());
  }

  initialize() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());

    if (this.childComponents) {
      // Monitor childComponent changes (view and edit modes can use different components)
      this.subscriptions.push(
        this.childComponents.changes.subscribe(() => setTimeout(() => this.initialize()))
      );
    }

    this.formControl = this.form.get(this.name) as FormControl;
    this.subscriptions.push(
      this.formControl.statusChanges.subscribe(change => {
        if (this.formControl.hasError('scrollTo')) {
          this.formField?.nativeElement.scrollIntoView({ behavior: 'smooth' });
        }
      })
    );

    this.childComponents?.reduce((previousValue, currentValue) => {
      if (currentValue instanceof ElementRef && currentValue.nativeElement) {
        previousValue.push(currentValue.nativeElement);
      } else if (currentValue instanceof MatSelect && currentValue._elementRef?.nativeElement) {
        previousValue.push(currentValue._elementRef.nativeElement);
      } else if (currentValue instanceof VardaAutocompleteSelectorComponent && currentValue.textInput?.nativeElement) {
        previousValue.push(currentValue.textInput.nativeElement);
      }
      return previousValue;
    }, []).forEach(nativeElement => {
      nativeElement.name = nativeElement.name || this.name;
      nativeElement.placeholder = this.placeholder;
      nativeElement.setAttribute('aria-labelledby', this.labelId);
      nativeElement.setAttribute('robot', this.name);
      this.subscriptions.push(
        fromEvent(nativeElement, 'focus').subscribe(() => this.focusStatus$.next(true)),
        fromEvent(nativeElement, 'blur').subscribe(() => this.focusStatus$.next(false))
      );
    });

    if (this.radioGroup) {
      this.subscriptions.push(this.formControl.valueChanges.subscribe((change: Observable<boolean>) => {
        this.focusStatus$.next(true);
        setTimeout(() => this.focusStatus$.next(false), 2000);
      }));
    } else if (this.datePicker) {
      this.datePicker.attrName = this.datePicker.attrName || this.name;
      this.subscriptions.push(this.datePicker.focusObservable().subscribe(value => this.focusStatus$.next(value)));
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription?.unsubscribe());
  }
}
