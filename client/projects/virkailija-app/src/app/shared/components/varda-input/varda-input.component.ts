import { Component, EventEmitter, forwardRef, Input, Output, ViewChild } from '@angular/core';
import {
  AbstractControl,
  ControlValueAccessor, NG_VALIDATORS,
  NG_VALUE_ACCESSOR,
  NgModel,
  ValidationErrors,
  Validator
} from '@angular/forms';

@Component({
  selector: 'app-varda-input',
  templateUrl: './varda-input.component.html',
  styleUrls: ['./varda-input.component.css'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => VardaInputComponent),
      multi: true
    },
    {
      provide: NG_VALIDATORS,
      useExisting: VardaInputComponent,
      multi: true
    }
  ]
})
export class VardaInputComponent implements ControlValueAccessor, Validator {
  @ViewChild('inputObject') inputObject: NgModel;
  @Input() name: string;
  @Input() id: string;
  @Input() type: string;
  @Input() placeholder: string;
  @Input() required? = false;
  @Input() readonly? = false;
  @Input() minlength?: number;
  @Input() errorMap?: Array<{ key: string; value: string }>;
  @Output() readonly keydownEnter: EventEmitter<Event> = new EventEmitter<Event>();

  disabled = false;
  inputValue: any;

  registerOnChange(fn: any): void {
    this.propagateChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.propagateTouch = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }

  writeValue(obj: any): void {
    this.inputValue = obj;
  }

  onBlur() {
    this.propagateTouch();
  }

  onInput(event: Event) {
    this.propagateChange(this.inputValue);
  }

  onKeydownEnter(event: Event) {
    this.keydownEnter.emit(event);
  }

  validate(control: AbstractControl): ValidationErrors | null {
    return this.inputObject?.errors;
  }

  private propagateChange = (_: any) => { };
  private propagateTouch = () => { };
}
