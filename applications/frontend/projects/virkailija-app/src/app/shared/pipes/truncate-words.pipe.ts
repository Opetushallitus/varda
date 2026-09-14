import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
    name: 'truncateWords',
    standalone: false
})

export class TruncateWordsPipe implements PipeTransform {
  transform(value: string, limit: number): string {
    const words = value.split(' ');

    if (words.length > limit) {
      return words.slice(0, limit).join(' ') + '...';
    }

    return value;
  }
}
