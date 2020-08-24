import { Pipe, PipeTransform } from '@angular/core';
import { VardaDateService } from '../../varda-main/services/varda-date.service';
import { DatePipe } from '@angular/common';

@Pipe({
  name: 'vardaDate'
})
export class VardaDate extends DatePipe implements PipeTransform {
  transform(value: any, args?: any): any {
    return super.transform(value, VardaDateService.uiDateFormat);
  }
}
