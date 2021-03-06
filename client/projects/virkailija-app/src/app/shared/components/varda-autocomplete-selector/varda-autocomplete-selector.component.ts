import {
  Component,
  ElementRef,
  EventEmitter,
  forwardRef,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
  ViewChild
} from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { BehaviorSubject } from 'rxjs';
import { MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';

interface OptionFormat {
  format: string;
  properties: Array<string>;
}

@Component({
  selector: 'app-varda-autocomplete-selector',
  templateUrl: './varda-autocomplete-selector.component.html',
  styleUrls: ['./varda-autocomplete-selector.component.css'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => VardaAutocompleteSelectorComponent),
      multi: true
    }
  ]
})
export class VardaAutocompleteSelectorComponent<T> implements ControlValueAccessor, OnChanges {
  @Input() optionFormat: OptionFormat = {format: '{0}', properties: null};
  @Input() options: Array<T>;
  @Input() placeholder: string;
  @Input() nullValue: any = null;
  @Input() nullOptionLabel = '-';
  @Input() invalidInputLabel = '';
  @ViewChild('textInput') textInput: ElementRef<HTMLInputElement>;

  inputValue = '';
  filteredOptions: BehaviorSubject<Array<T>> = new BehaviorSubject<Array<T>>([]);
  selectedOption: T;
  isNoResults = false;

  private propagateChange = (_: any) => {};
  private propagateTouch = () => {};

  constructor() { }

  inputChange(event: Event) {
    this.inputValue = '';
    this.selectedOption = this.nullValue;
    const targetValue = (<HTMLInputElement> event.target).value;
    const results = this.options.filter(option => {
      return this.getFormattedOption(option).toLowerCase().includes(targetValue.toLowerCase());
    });

    if (results.length === 0) {
      this.isNoResults = true;
      this.filteredOptions.next([]);
    } else {
      this.isNoResults = false;
      this.filteredOptions.next(results);
    }

    if (targetValue === '') {
      this.selectedOption = this.nullValue;
      this.propagateChange(this.nullValue);
    }
  }

  autocompleteSelected(event: MatAutocompleteSelectedEvent) {
    const option = event.option.value;
    this.selectedOption = option;
    this.filteredOptions.next(this.options);
    this.textInput.nativeElement.blur();
    this.propagateChange(option);
    this.fillTextInput(option);
  }

  isOptionInvalid(): boolean {
    if (!this.textInput) {
      return false;
    }
    return this.textInput.nativeElement.value !== '' && this.selectedOption === this.nullValue;
  }

  getFormattedOption(option: T) {
    if (option === this.nullValue) {
      return '';
    }

    let result = this.optionFormat.format;
    if (!this.optionFormat.properties && typeof option === 'string') {
      result = result.replace('{0}', option);
    } else {
      for (let i = 0; i < this.optionFormat.properties.length; i++) {
        result = result.replace(`{${i}}`, option[this.optionFormat.properties[i]]);
      }
    }
    return result;
  }

  fillTextInput(value: T) {
    if (this.textInput) {
      this.textInput.nativeElement.value = this.getFormattedOption(value);
    }
  }

  reset() {
    this.filteredOptions.next(this.options);
    this.selectedOption = this.nullValue;
    this.propagateChange(this.nullValue);

    if (this.textInput) {
      this.textInput.nativeElement.blur();
      this.textInput.nativeElement.value = '';
    }
  }

  writeValue(value: T) {
    this.selectedOption = value;
    this.fillTextInput(value);
  }

  registerOnChange(fn: any) {
    this.propagateChange = fn;
  }

  registerOnTouched(fn: any) {
    this.propagateTouch = fn;
  }

  ngOnChanges(changes: SimpleChanges): void {
    this.reset();
  }
}
