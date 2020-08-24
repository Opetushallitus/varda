import { Injectable } from '@angular/core';
import * as moment from 'moment';
import { Moment } from 'moment';

@Injectable()
export class VardaDateService {
  public static vardaDefaultDateFormat = 'DD.MM.YYYY';
  public static uiDateFormat = 'd.M.yyyy';
  public static vardaApiDateFormat = 'YYYY-MM-DD';

  /**
   * Varda UI date: view values are always DD.MM.YYYY. Datepicker returns Moment object. See https://material.angular.io/components/datepicker
   * ..or d.M.yyyy
   * Varda API date: YYYY-MM-DD
   */

  constructor() { }

  momentToVardaDate(date: Moment): string {
    let formattedDate = null;
    if (date) {
      formattedDate = date.format(VardaDateService.vardaApiDateFormat);
    }
    return formattedDate;
  }

  vardaDateToMoment(date: string): Moment {
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

}
