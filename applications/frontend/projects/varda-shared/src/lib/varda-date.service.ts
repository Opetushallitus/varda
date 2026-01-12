import { Injectable } from '@angular/core';
// https://github.com/jvandemo/generator-angular2-library/issues/221#issuecomment-355945207
import { DateTime } from 'luxon';

@Injectable({
  providedIn: 'root',
})
export class VardaDateService {
  public static vardaDefaultDateFormat = 'dd.MM.yyyy';
  public static uiDateFormat = 'd.M.yyyy';
  public static uiDateMinuteFormat = 'dd.MM.yyyy HH:mm';
  public static uiLongTimeFormat = 'dd.MM.yyyy HH:mm:ss';
  public static vardaApiDateFormat = 'yyyy-MM-dd';
  public static henkilostoReleaseDate = new Date('2020-09-01');
  public static taydennyskoulutusLatestDate = new Date('2024-12-31');
  public static ISODateTimeFormat = "yyyy-MM-dd'T'HH:mm:ssZZ";
  public static uiDateTimezone = {zone: "utc"};

  constructor() { }

  luxonToVardaDate(date: DateTime): string | null {
    let formattedDate = null;
    if (date && date.isValid) {
      formattedDate = date.toFormat(VardaDateService.vardaApiDateFormat);
    }
    return formattedDate;
  }

  luxonToISODateTime(date: DateTime): string | null {
    let formattedDate = null;
    if (date && date.isValid) {
      formattedDate = date.toFormat(VardaDateService.ISODateTimeFormat);
    }
    return formattedDate;
  }

  luxonToUiDate(date: DateTime): string | null {
    let formattedDate = null;
    if (date && date.isValid) {
      formattedDate = date.toFormat(VardaDateService.uiDateFormat);
    }
    return formattedDate;
  }

  vardaDateToLuxon(date: string | null | undefined): DateTime | null {
    if (!date || typeof date !== 'string') {
      return null;
    }

    const luxonDate = DateTime.fromFormat(date, VardaDateService.vardaApiDateFormat, VardaDateService.uiDateTimezone);
    return luxonDate.isValid ? luxonDate : null;
  }

  vardaDateToUIStrDate(date: string): string {
    if (!date) {
      return '';
    }

    const parsedDate = DateTime.fromFormat(date, VardaDateService.vardaApiDateFormat);
    if (!parsedDate.isValid) {
      return '';
    }

    return parsedDate.toFormat(VardaDateService.vardaDefaultDateFormat);
  }

  date1IsAfterDate2(date1: DateTime, date2: DateTime | null): boolean {
    if (!date2 || !date2.isValid) {
      return true;
    }
    return date1.isValid && date1 > date2;
  }

  date1isAfterOrSameAsDate2(date1: DateTime, date2: DateTime | null): boolean {
    if (!date2 || !date2.isValid) {
      return true;
    }
    return date1.isValid && (date1 >= date2);
  }

  date1IsBeforeDate2(date1: DateTime, date2: DateTime | null): boolean {
    if (!date2 || !date2.isValid) {
      return true;
    }
    return date1.isValid && date1 < date2;
  }

  apiDateToUiDate(date?: string | null): string {
    if (!date) {
      return '';
    }
    const luxonDate = DateTime.fromFormat(date, VardaDateService.vardaApiDateFormat);
    if (!luxonDate.isValid) {
      return '';
    }
    return luxonDate.toFormat(VardaDateService.uiDateFormat);
  }

  apiDateTimeToUiDate(dateTime?: string | null): string {
    if (!dateTime) {
      return '';
    }
    const luxonDate = DateTime.fromFormat(dateTime, VardaDateService.ISODateTimeFormat);
    if (!luxonDate.isValid) {
      return '';
    }
    return luxonDate.toFormat(VardaDateService.uiDateFormat);
  }

  getDateDisplayValue(date: string): string {
    const dateUi = this.apiDateToUiDate(date);
    return dateUi ? dateUi : '-';
  }

  getDateRangeDisplayValue(startDate: string, endDate: string): string {
    const startDateUi = this.apiDateToUiDate(startDate);
    const endDateUi = this.apiDateToUiDate(endDate);

    if (!startDateUi && !endDateUi) {
      return '-';
    }

    let result = '';
    result += startDateUi ? `${startDateUi} -` : '-';
    result += endDateUi ? ` ${endDateUi}` : '';

    return result;
  }
}
