import { DatePipe } from '@angular/common';
import { Pipe, PipeTransform } from '@angular/core';

export enum HuoltajaDateFormats {
  date = 'd.M.yyyy',
  month = 'MM/yyyy'
}

@Pipe({
  name: 'huoltajaDate'
})
export class HuoltajaDatePipe extends DatePipe implements PipeTransform {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  transform(value: string, args?: any): any {
    return super.transform(value, HuoltajaDateFormats.date);
  }
}

@Pipe({
  name: 'huoltajaMonth'
})
export class HuoltajaMonthPipe extends DatePipe implements PipeTransform {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  transform(value: string, args?: any): any {
    return super.transform(value, HuoltajaDateFormats.month);
  }

}
