import { Injectable } from '@angular/core';
import * as moment from 'moment';

@Injectable()
export class VardaDateService {

  public vardaDefaultDateFormat = 'DD.MM.YYYY';
  public vardaApiDateFormat = 'YYYY-MM-DD';

  /**
   * Varda UI date: view values are always DD.MM.YYYY. Datepicker returns object. See https://github.com/kekeh/mydatepicker
   * Varda API date: YYYY-MM-DD
   */

  constructor() { }

  uiDateToVardaDate(date: any): string {
    let formattedDate = null;
    if (date && date.hasOwnProperty('date')) {
      const dateObj = date.date;
      const dateObjStr = `${dateObj.day}.${dateObj.month}.${dateObj.year}`;
      const momentObj = moment(dateObjStr, this.vardaDefaultDateFormat);
      formattedDate = momentObj.format(this.vardaApiDateFormat);
    }
    return formattedDate;
  }

  uiDateToMoment(date: any): moment.Moment {
    let momentObj = null;
    if (date && date.hasOwnProperty('date')) {
      const dateObj = date.date;
      const dateObjStr = `${dateObj.day}.${dateObj.month}.${dateObj.year}`;
      momentObj = moment(dateObjStr, this.vardaDefaultDateFormat);
    }
    return momentObj;
  }

  vardaDateToUIDate(date: string): any {
    const dateParts = date.split('-');
    const yearStr = dateParts[0];
    const monthStr = dateParts[1];
    const dayStr = dateParts[2];
    const datePickerObj = {date: {year: parseInt(yearStr), month: parseInt(monthStr), day: parseInt(dayStr)}};
    return datePickerObj;
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
    const momentObj = moment(dateObjStr, this.vardaDefaultDateFormat);
    formattedDate = momentObj.format(this.vardaDefaultDateFormat);
    return formattedDate;
  }

  date1IsAfterDate2(date1: moment.Moment, date2: moment.Moment): boolean {
    if (!date2) {
      return true;
    }
    const isAfter = date1.isAfter(date2);
    return isAfter;
  }

  date1isAfterOrSameAsDate2(date1: moment.Moment, date2: moment.Moment): boolean {
    if (!date2) {
      return true;
    }
    const isAfterOrSame = date1.isSameOrAfter(date2);
    return isAfterOrSame;
  }

  date1IsBeforeDate2(date1: moment.Moment, date2: moment.Moment): boolean {
    if (!date2) {
      return true;
    }
    const isBefore = date1.isBefore(date2);
    return isBefore;
  }

}
