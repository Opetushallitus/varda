import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
    name: 'keys',
    standalone: false
})
export class KeysPipe implements PipeTransform {

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  transform(value: any, args?: any): any {
    return Object.keys(value);
  }
}
