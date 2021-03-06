import {
  Component,
  EventEmitter,
  forwardRef,
  Input,
  OnInit,
  Output,
  ViewChild,
  ViewEncapsulation
} from '@angular/core';
import { MatDatepickerInputEvent } from '@angular/material/datepicker';
import { DateAdapter } from '@angular/material/core';
import { Moment } from 'moment';
import * as moment from 'moment';
import { AbstractControl, ControlValueAccessor, FormControl, NG_VALIDATORS, NG_VALUE_ACCESSOR } from '@angular/forms';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../../core/auth/auth.service';
import { VardaDatepickerHeaderComponent } from './varda-datepicker-header/varda-datepicker-header.component';
import { Observable, Subject, BehaviorSubject } from 'rxjs';

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
export class VardaDatepickerComponent implements OnInit, ControlValueAccessor {
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
  @Output() readonly dateInput: EventEmitter<VardaDatepickerEvent> = new EventEmitter<VardaDatepickerEvent>();
  @Output() readonly dateChange: EventEmitter<VardaDatepickerEvent> = new EventEmitter<VardaDatepickerEvent>();
  // Emit true if focusin, false if focusout
  @Output() readonly focusChange: EventEmitter<boolean> = new EventEmitter<boolean>();
  // Emit true if calendar is opened, false if closed
  @Output() readonly calendarChange: EventEmitter<boolean> = new EventEmitter<boolean>();
  @ViewChild('matPicker') pickerControl!: AbstractControl;

  VardaDatepickerHeaderComponent = VardaDatepickerHeaderComponent;
  disabled = false;
  matDateModel: Moment = moment();
  private focus$ = new Subject<boolean>();
  private lastValidState = true;
  private propagateChange = (_: any) => { };
  private propagateTouch = () => { };

  constructor(
    private dateAdapter: DateAdapter<any>,
    private translateService: TranslateService,
  ) { }

  ngOnInit(): void {
    if (!this.placeholder) {
      this.placeholder = this.translateService.instant('label.date-placeholder');
    }

    if (this.translateService.getDefaultLang() === 'sv') {
      this.dateAdapter.setLocale('sv-SV');
    } else {
      this.dateAdapter.setLocale('fi-FI');
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

  validate(control: FormControl) {
    if (this.pickerControl) {
      return this.pickerControl.validator(control);
    }
  }
}
