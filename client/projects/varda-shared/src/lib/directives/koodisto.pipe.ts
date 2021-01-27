import { Pipe, PipeTransform } from '@angular/core';
import { Observable } from 'rxjs';
import { take } from 'rxjs/operators';
import { KoodistoEnum } from '../dto/koodisto-models';
import { VardaKoodistoService } from '../koodisto.service';

interface KoodistoPipeArgs {
  koodisto: KoodistoEnum;
}

@Pipe({
  name: 'koodisto'
})
export class KoodistoPipe implements PipeTransform {
  constructor(private koodistoService: VardaKoodistoService) {

  }

  transform(code: string, args: KoodistoPipeArgs): unknown {
    return new Observable(obs => {
      this.koodistoService.getCodeValueFromKoodisto(args.koodisto, code).pipe(take(1)).subscribe(koodistoValue => {
        obs.next(koodistoValue.name);
        obs.complete();
      });
    });
  }

}
