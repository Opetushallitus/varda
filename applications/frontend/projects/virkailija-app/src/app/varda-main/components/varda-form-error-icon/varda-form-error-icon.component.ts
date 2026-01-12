import { Component, Input, OnChanges, OnDestroy, SimpleChanges } from '@angular/core';
import { Subscription } from 'rxjs';
import { KoodistoEnum, VardaKoodistoService } from 'varda-shared';
import { PuutteellinenErrorDTO } from '../../../utilities/models/dto/varda-puutteellinen-dto.model';

@Component({
    selector: 'app-varda-form-error-icon',
    templateUrl: './varda-form-error-icon.component.html',
    styleUrls: ['./varda-form-error-icon.component.css'],
    standalone: false
})
export class VardaFormErrorIconComponent implements OnChanges, OnDestroy {
  @Input() errors: Array<PuutteellinenErrorDTO>;
  errorTitle: string;
  subscriptions: Array<Subscription> = [];
  constructor(private koodistoService: VardaKoodistoService) { }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  ngOnChanges(changes: SimpleChanges): void {
    if (this.errors?.length) {
      this.subscriptions.push(
        this.koodistoService.getCodeValueFromKoodisto(KoodistoEnum.virhe, this.errors[0].error_code).subscribe(codeValue => {
          this.errorTitle = codeValue?.name || this.errors[0].description;
        })
      );
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
}
