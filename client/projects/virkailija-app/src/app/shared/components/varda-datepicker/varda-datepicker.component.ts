import {
  Component,
  EventEmitter,
  forwardRef,
  Input, OnChanges,
  OnInit,
  Output, SimpleChanges,
  ViewChild,
  ViewEncapsulation
} from '@angular/core';
import { MatDatepickerInputEvent } from '@angular/material/datepicker';
import { DateAdapter } from '@angular/material/core';
import { Moment } from 'moment';
import * as moment from 'moment';
import {
  AbstractControl,
  ControlValueAccessor,
  NG_VALIDATORS,
  NG_VALUE_ACCESSOR, NgModel, ValidationErrors,
  Validator
} from '@angular/forms';
import { TranslateService } from '@ngx-translate/core';
import { VardaDatepickerHeaderComponent } from './varda-datepicker-header/varda-datepicker-header.component';
import { Observable, Subject } from 'rxjs';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

export interface VardaDatepickerEvent {
  valid: boolean;
  value: Moment;
}

@Component({
  selector: 'app-varda-datepicker',
  templateUrl: './varda-datepicker.component.html',
  styleUrls: ['./varda-datepicker.component.css'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => VardaDatepickerComponent),
      multi: true
    },
    {
      provide: NG_VALIDATORS,
      useExisting: VardaDatepickerComponent,
      multi: true
    }
  ],
  encapsulation: ViewEncapsulation.None
})
export class VardaDatepickerComponent implements OnInit, OnChanges, ControlValueAccessor, Validator {
  @Input() placeholder: string;
  @Input() required = false;
  @Input() readonly = false;
  @Input() startAt: Date;
  @Input() min: Date;
  @Input() max: Date;
  @Input() dateFilter: any;
  @Input() attrAriaLabelledBy?: string;
  @Input() attrName?: string;
  @Input() attrDataFieldname?: string;
  @Input() attrAriaRequired?: boolean;
  @Input() attrAriaDescribedBy?: string;
  @Input() attrDataParentContainer?: string;
  @Input() errorMap?: Array<{ key: string; value: string }> = [];
  @Input() isTouched?: boolean;
  @Output() readonly dateInput: EventEmitter<VardaDatepickerEvent> = new EventEmitter<VardaDatepickerEvent>();
  @Output() readonly dateChange: EventEmitter<VardaDatepickerEvent> = new EventEmitter<VardaDatepickerEvent>();
  // Emit true if focusin, false if focusout
  @Output() readonly focusChange: EventEmitter<boolean> = new EventEmitter<boolean>();
  // Emit true if calendar is opened, false if closed
  @Output() readonly calendarChange: EventEmitter<boolean> = new EventEmitter<boolean>();
  @ViewChild('matPicker', {read: NgModel}) pickerControl: NgModel;

  VardaDatepickerHeaderComponent = VardaDatepickerHeaderComponent;
  disabled = false;
  matDateModel: Moment = moment();
  private focus$ = new Subject<boolean>();
  private lastValidState = true;

  constructor(
    private dateAdapter: DateAdapter<any>,
    private translateService: TranslateService,
  ) { }

  ngOnInit(): void {
    if (!this.placeholder) {
      this.placeholder = this.translateService.instant(VirkailijaTranslations.datepicker_placeholder);
    }

    if (this.translateService.currentLang === 'sv') {
      this.dateAdapter.setLocale('sv-SV');
    } else {
      this.dateAdapter.setLocale('fi-FI');
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.isTouched) {
      setTimeout(() => this.pickerControl?.control.markAsTouched());
    }
  }

  onDateInput(event: MatDatepickerInputEvent<any>) {
    this.propagateTouch();
    this.propagateChange(this.matDateModel);
    this.dateInput.emit({ valid: this.pickerControl.valid, value: event.value });
  }

  onDateChange(event: MatDatepickerInputEvent<any>) {
    this.dateChange.emit({ valid: this.pickerControl.valid, value: event.value });
  }

  onFocus() {
    this.focusChange.emit(true);
    this.focus$.next(true);
  }

  onBlur() {
    this.propagateTouch();
    this.focusChange.emit(false);
    this.focus$.next(false);
  }

  focusObservable(): Observable<boolean> {
    return this.focus$.asObservable();
  }

  // Handle input events so we get feedback before blur, while user is typing
  onInput(event: Event) {
    const target = event.target as HTMLInputElement;
    if (target.value === null || target.value === '' || this.lastValidState !== this.pickerControl.valid) {
      this.propagateChange(this.matDateModel);
      this.dateInput.emit({ valid: this.pickerControl.valid, value: this.matDateModel });
    }
    this.lastValidState = this.pickerControl.valid;
  }

  onCalendarOpened() {
    this.calendarChange.emit(true);
  }

  onCalendarClosed() {
    this.calendarChange.emit(false);
  }

  writeValue(value: any) {
    this.pickerControl?.reset();
    this.matDateModel = value;
  }

  registerOnChange(fn: any) {
    this.propagateChange = fn;
  }

  registerOnTouched(fn: any) {
    this.propagateTouch = fn;
  }

  setDisabledState(isDisabled: boolean) {
    this.disabled = isDisabled;
  }

  validate(control: AbstractControl): ValidationErrors | null {
    if (this.pickerControl) {
      return this.pickerControl.validator(control);
    }
  }

  private propagateChange = (_: any) => { };
  private propagateTouch = () => { };
}
