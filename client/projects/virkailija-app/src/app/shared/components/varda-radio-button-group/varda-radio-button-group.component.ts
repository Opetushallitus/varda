import {
  Component,
  OnInit,
  OnDestroy,
  Input,
  Output,
  EventEmitter,
  QueryList,
  ContentChildren,
  forwardRef,
  ChangeDetectorRef,
  AfterContentInit
} from '@angular/core';
import { VardaRadioButtonComponent } from './varda-radio-button/varda-radio-button.component';
import { ControlValueAccessor, NG_VALUE_ACCESSOR, NgModel } from '@angular/forms';
import { Subscription } from 'rxjs';

enum Breakpoints {
  xs = 'xs',
  sm = 'sm',
  md = 'md',
  lg = 'lg',
  xl = 'xl',
}

export interface RadioButtonResponse {
  event: Event;
  value: any;
}


@Component({
  selector: 'app-varda-radio-button-group',
  templateUrl: './varda-radio-button-group.component.html',
  styleUrls: ['./varda-radio-button-group.component.css'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => VardaRadioButtonGroupComponent),
      multi: true
    }
  ]
})
export class VardaRadioButtonGroupComponent implements OnInit, OnDestroy, AfterContentInit, ControlValueAccessor {
  @Input() name: string;
  @Input() class: string;
  @Input() responsive: Breakpoints;
  @Input() wrap: Breakpoints;
  @Input() ngModel?: NgModel;
  @Input() _value: any;
  @Output() readonly valueChanged: EventEmitter<RadioButtonResponse> = new EventEmitter<RadioButtonResponse>();
  @ContentChildren(forwardRef(() => VardaRadioButtonComponent), { descendants: true }) radioButtons: QueryList<VardaRadioButtonComponent>;
  classes: string[];
  radioOnChange: EventEmitter<RadioButtonResponse> = new EventEmitter(true);
  radioOnChangeSubscription: Subscription;

  constructor(private _changeDetector: ChangeDetectorRef) { }

  ngOnInit() {
    this.classes = [
      this.class,
      this.wrap ? `wrap-${this.wrap}` : null,
      this.responsive ? `responsive-${this.responsive}` : null,
    ].filter(c => c);

    this.radioOnChangeSubscription = this.radioOnChange.subscribe(obj => {
      if (this._value !== obj.value) {
        this.writeValue(obj.value);
        this.propagateChange(obj.value);
        this.valueChanged.emit(obj);
      }
    });
  }

  ngAfterContentInit() {
    this.radioButtons.forEach(radio => {
      radio.name = this.name;
      radio.valueChange = this.radioOnChange;
    });
  }

  ngOnDestroy() {
    this.radioOnChangeSubscription.unsubscribe();
  }

  writeValue(value: any) {
    this._value = value;
    this.radioButtons.forEach(radio => {
      radio.checked = value === radio.value;
    });

    this._changeDetector.markForCheck();
  }

  propagateChange = (_: any) => {};

  registerOnChange(fn: any) {
    this.propagateChange = fn;
  }

  registerOnTouched(fn: any) {}
}
