import { Injectable } from '@angular/core';
// https://github.com/jvandemo/generator-angular2-library/issues/221#issuecomment-355945207
import moment from 'moment';

@Injectable({
  providedIn: 'root',
})
export class VardaDateService {
  public static vardaDefaultDateFormat = 'DD.MM.YYYY';
  public static uiDateFormat = 'd.M.yyyy';
  public static uiLongTimeFormat = 'dd.MM.yyyy HH:mm:ss';
  public static vardaApiDateFormat = 'YYYY-MM-DD';
  public static uiDateFormatMoment = 'D.M.YYYY';
  public static henkilostoReleaseDate = new Date('2020-09-01');
  public static ISODateTimeFormat = 'YYYY-MM-DDTHH:mm:ssZ';

  /**
   * Varda UI date: view values are always DD.MM.YYYY. Datepicker returns Moment object. See https://material.angular.io/components/datepicker
   * ..or d.M.yyyy
   * Varda API date: YYYY-MM-DD
   */

  constructor() { }

  momentToVardaDate(date: moment.Moment): string {
    let formattedDate = null;
    if (date) {
      formattedDate = date.format(VardaDateService.vardaApiDateFormat);
    }
    return formattedDate;
  }

  momentToISODateTime(date: moment.Moment): string {
    let formattedDate = null;
    if (date) {
      formattedDate = date.format(VardaDateService.ISODateTimeFormat);
    }
    return formattedDate;
  }

  momentToUiDate(date: moment.Moment): string {
    let formattedDate = null;
    if (date) {
      formattedDate = date.format(VardaDateService.uiDateFormatMoment);
    }
    return formattedDate;
  }

  vardaDateToMoment(date: string): moment.Moment {
    const momentDate = moment(date, VardaDateService.vardaApiDateFormat);
    if (!momentDate.isValid()) {
      return null;
    }
    return moment(date, VardaDateService.vardaApiDateFormat);
  }

  vardaDateToUIStrDate(date: string): string {
    let formattedDate = null;
    if (!date) {
      formattedDate = '';
      return formattedDate;
    }
    const dateParts = date.split('-');
    const yearStr = dateParts[0];
    const monthStr = dateParts[1];
    const dayStr = dateParts[2];
    const dateObjStr = `${dayStr}.${monthStr}.${yearStr}`;
    const momentObj = moment(dateObjStr, VardaDateService.vardaDefaultDateFormat);
    formattedDate = momentObj.format(VardaDateService.vardaDefaultDateFormat);
    return formattedDate;
  }

  date1IsAfterDate2(date1: moment.Moment, date2: moment.Moment): boolean {
    if (!date2) {
      return true;
    }
    return date1.isAfter(date2);
  }

  date1isAfterOrSameAsDate2(date1: moment.Moment, date2: moment.Moment): boolean {
    if (!date2) {
      return true;
    }
    return date1.isSameOrAfter(date2);
  }

  date1IsBeforeDate2(date1: moment.Moment, date2: moment.Moment): boolean {
    if (!date2) {
      return true;
    }
    return date1.isBefore(date2);
  }

  apiDateToUiDate(date: string): string {
    const momentDate = moment(date, VardaDateService.vardaApiDateFormat);
    if (!momentDate.isValid()) {
      return '';
    }
    return momentDate.format(VardaDateService.uiDateFormatMoment);
  }

  apiDateTimeToUiDate(dateTime: string): string {
    const momentDate = moment(dateTime, VardaDateService.ISODateTimeFormat);
    if (!momentDate.isValid()) {
      return '';
    }
    return momentDate.format(VardaDateService.uiDateFormatMoment);
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
