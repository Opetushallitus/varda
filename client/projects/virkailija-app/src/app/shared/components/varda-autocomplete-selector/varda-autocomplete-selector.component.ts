import {
  Component,
  ElementRef,
  forwardRef,
  Input,
  OnChanges,
  SimpleChanges,
  ViewChild,
  ViewEncapsulation
} from '@angular/core';
import {
  ControlValueAccessor,
  NG_VALUE_ACCESSOR
} from '@angular/forms';
import { BehaviorSubject } from 'rxjs';
import { MatAutocompleteSelectedEvent, MatAutocompleteTrigger } from '@angular/material/autocomplete';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { CodeDTO, KoodistoEnum, VardaKoodistoService } from 'varda-shared';
import { CdkVirtualScrollViewport } from '@angular/cdk/scrolling';

interface OptionFormat {
  format: string;
  properties: Array<string>;
}

// Height of mat-option is 48px
const OPTION_HEIGHT = 48;
// max-height of mat-autocomplete-panel is 256px
const MAX_HEIGHT = 256;

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
  ],
  encapsulation: ViewEncapsulation.None
})
export class VardaAutocompleteSelectorComponent<T> implements ControlValueAccessor, OnChanges {
  @ViewChild('textInput', {read: ElementRef}) textInput: ElementRef<HTMLInputElement>;
  @ViewChild('textInput', {read: MatAutocompleteTrigger}) autocompleteTrigger: MatAutocompleteTrigger;
  @ViewChild(CdkVirtualScrollViewport, {static: true}) virtualViewport: CdkVirtualScrollViewport;
  @Input() optionFormat: OptionFormat = {format: '{0}', properties: null};
  @Input() options: Array<T>;
  @Input() placeholder: string;
  @Input() nullValue: any = null;
  @Input() nullOptionLabel = '-';
  @Input() isNullOption = true;
  @Input() invalidInputLabel = '';
  @Input() disabled = false;
  @Input() koodisto: KoodistoEnum;
  @Input() returnCodeValue = false;
  @Input() displayCodeValue = false;

  i18n = VirkailijaTranslations;
  filteredOptions: BehaviorSubject<Array<T>> = new BehaviorSubject<Array<T>>([]);
  selectedOption: T;
  isNoResults = false;
  isInvalid = false;
  viewportHeight = 0;
  inputValue: any;

  constructor(private koodistoService: VardaKoodistoService) { }

  inputChange(event: Event) {
    const targetValue = (event.target as HTMLInputElement).value.toLowerCase();
    const results = this.options.filter(option => this.getFormattedOption(option).toLowerCase().includes(targetValue));
    this.isNoResults = results.length === 0;
    this.setFilteredOptions(results);

    if (results.length === 1 && (this.getFormattedOption(results[0]).toLowerCase() === targetValue ||
      (this.koodisto && (results[0] as unknown as CodeDTO).code_value.toLowerCase() === targetValue))) {
      // Select option immediately if there is only 1 result and input matches to option or code_value
      this.isInvalid = false;
      this.isNoResults = false;
      this.selectedOption = results[0];
      this.fillTextInput();
      this.emitValueChanged();
      this.textInput.nativeElement.blur();
      this.autocompleteTrigger.closePanel();
    } else {
      // 0 or more than 1 results
      // Set invalid if
      this.isInvalid = targetValue !== '' || !this.isNullOption;
      if (this.selectedOption !== this.nullValue) {
        this.selectedOption = this.nullValue;
        this.propagateChange(this.nullValue);
      }
    }
  }

  autocompleteSelected(event: MatAutocompleteSelectedEvent) {
    this.isInvalid = false;
    this.selectedOption = event.option.value;
    this.setFilteredOptions(this.options);
    this.textInput.nativeElement.blur();
    this.emitValueChanged();
    this.fillTextInput();
  }

  autocompleteOpened() {
    this.virtualViewport?.setRenderedContentOffset(0);
    const index = this.selectedOption === this.nullValue ? 0 : this.filteredOptions.getValue().indexOf(this.selectedOption);
    setTimeout(() => this.virtualViewport?.scrollToIndex(index));
  }

  emitValueChanged() {
    let value = this.selectedOption;
    if (this.koodisto && this.returnCodeValue) {
      value = (this.selectedOption as unknown as CodeDTO).code_value as unknown as T;
    }
    this.propagateChange(value);
  }

  isOptionInvalid(): boolean {
    if (!this.textInput) {
      return false;
    }
    return this.textInput.nativeElement.value !== '' && this.selectedOption === this.nullValue;
  }

  setInvalid() {
    this.isInvalid = true;
  }

  getFormattedOption(option: T) {
    if (option === this.nullValue) {
      return '';
    }

    if (this.koodisto) {
      return this.koodistoService.getCodeFormattedValue('long', option as unknown as CodeDTO);
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

  fillTextInput() {
    setTimeout(() => {
      if (!this.textInput) {
        return;
      }

      if (this.selectedOption) {
        if (this.koodisto && this.displayCodeValue) {
          this.textInput.nativeElement.value = (this.selectedOption as unknown as CodeDTO).code_value;
        } else {
          this.textInput.nativeElement.value = this.getFormattedOption(this.selectedOption);
        }
      } else {
        this.textInput.nativeElement.value = '';
      }
    });
  }

  reset() {
    this.setFilteredOptions(this.options);
    this.selectedOption = this.nullValue;
    this.propagateChange(this.nullValue);

    if (this.textInput) {
      this.textInput.nativeElement.blur();
      this.textInput.nativeElement.value = '';
    }
  }

  setFilteredOptions(items: Array<T>) {
    this.filteredOptions.next(items);

    let actualHeight = 0;
    actualHeight += this.isNoResults ? OPTION_HEIGHT : 0;
    actualHeight += this.isNullOption ? OPTION_HEIGHT : 0;
    actualHeight += items.length * OPTION_HEIGHT;
    this.viewportHeight = actualHeight > MAX_HEIGHT ? MAX_HEIGHT : actualHeight;
  }

  setDisabledState(isDisabled: boolean) {
    this.disabled = isDisabled;
  }

  writeValue(value: T) {
    if (this.koodisto && this.returnCodeValue) {
      const options = this.options as Array<unknown> as Array<CodeDTO>;
      const valueAsString = value ? value as unknown as string : null;
      value = options.find(code => code.code_value === valueAsString) as unknown as T;
    }

    this.selectedOption = value;
    this.fillTextInput();
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

  propagateTouch = () => {};

  private propagateChange = (_: any) => {};
}
