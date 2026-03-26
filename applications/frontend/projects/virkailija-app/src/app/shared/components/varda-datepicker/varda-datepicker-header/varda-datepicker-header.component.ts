import { ChangeDetectionStrategy, ChangeDetectorRef, Component, Inject } from '@angular/core';
import { MatCalendar, MatCalendarHeader, MatDatepickerIntl } from '@angular/material/datepicker';
import { DateAdapter, MAT_DATE_FORMATS, MatDateFormats } from '@angular/material/core';

@Component({
    selector: 'app-varda-datepicker-header',
    templateUrl: './varda-datepicker-header.component.html',
    styleUrls: ['./varda-datepicker-header.component.css'],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: false
})
export class VardaDatepickerHeaderComponent<D> extends MatCalendarHeader<D> {
    constructor(private _calendar: MatCalendar<D>,
                private dateAdapter: DateAdapter<D>,
                @Inject(MAT_DATE_FORMATS) private dateFormats: MatDateFormats,
                private cdr: ChangeDetectorRef,
                private intl: MatDatepickerIntl) {
      super(intl, _calendar, dateAdapter, dateFormats, cdr);
  }

  // Overwrite https://github.com/angular/components/blob/aca253350c166fe1c04fbdcc75238647c8cd244f/src/material/datepicker/calendar.ts#L115
  /** Handles user clicks on the period label. */
  currentPeriodClicked(): void {
    this._calendar.currentView = this._calendar.currentView === 'month' ? 'year' : 'month';
  }
}
