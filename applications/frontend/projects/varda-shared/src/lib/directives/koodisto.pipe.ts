import { Pipe, PipeTransform } from '@angular/core';
import { Observable } from 'rxjs';
import { take } from 'rxjs/operators';
import { KoodistoEnum } from '../models/koodisto-models';
import { VardaKoodistoService } from '../koodisto.service';

interface KoodistoPipeArgs {
  koodisto: KoodistoEnum;
  format: 'short' | 'long';
}

@Pipe({
  name: 'koodisto'
})
export class KoodistoPipe implements PipeTransform {
  constructor(private koodistoService: VardaKoodistoService) { }

  transform(code: string, args: KoodistoPipeArgs): unknown {
    return new Observable(obs => {
      this.koodistoService.getCodeValueFromKoodisto(args.koodisto, code).pipe(take(1)).subscribe(koodistoValue => {
        obs.next(args.format === 'long' ? `${koodistoValue.name} (${koodistoValue.code_value})` : koodistoValue.name);
        obs.complete();
      });
    });
  }
}
