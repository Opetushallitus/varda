import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'vardaDate'
})
export class VardaDatePipe implements PipeTransform {

  transform(dateStr: string, args?: any): string {
    let rv = '';

    if (!dateStr) {
      return rv;
    }

    if (!args) {
        const dateParts = dateStr.split('-');
        const yearStr = dateParts[0];
        const monthStr = dateParts[1];
        const dayStr = dateParts[2];
        rv =  `${dayStr}.${monthStr}.${yearStr}`;
    }

    return rv;
  }

}
