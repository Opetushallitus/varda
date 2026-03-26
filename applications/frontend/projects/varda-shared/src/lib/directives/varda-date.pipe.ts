import { Pipe, PipeTransform } from '@angular/core';
import { DatePipe } from '@angular/common';
import { VardaDateService } from '../varda-date.service';

@Pipe({
    name: 'vardaDate',
    standalone: false
})
export class VardaDate extends DatePipe implements PipeTransform {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  transform(value: any, args?: any): any {
    return super.transform(value, VardaDateService.uiDateFormat);
  }
}

@Pipe({
    name: 'vardaDateMinutes',
    standalone: false
})
export class VardaDateMinutes extends DatePipe implements PipeTransform {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  transform(value: any, args?: any): any {
    return super.transform(value, VardaDateService.uiDateMinuteFormat);
  }
}

@Pipe({
    name: 'vardaLongDate',
    standalone: false
})
export class VardaLongDate extends DatePipe implements PipeTransform {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  transform(value: any, args?: any): any {
    return super.transform(value, VardaDateService.uiLongTimeFormat);
  }
}
