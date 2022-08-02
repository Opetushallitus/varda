import { Pipe, PipeTransform } from '@angular/core';
import { DatePipe } from '@angular/common';
import { VardaDateService } from '../varda-date.service';

@Pipe({
  name: 'vardaDate'
})
export class VardaDate extends DatePipe implements PipeTransform {
  transform(value: any, args?: any): any {
    return super.transform(value, VardaDateService.uiDateFormat);
  }
}

@Pipe({
  name: 'vardaLongDate'
})
export class VardaLongDate extends DatePipe implements PipeTransform {
  transform(value: any, args?: any): any {
    return super.transform(value, VardaDateService.uiLongTimeFormat);
  }
}
