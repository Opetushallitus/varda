import { AfterViewInit, Component, Input, OnChanges, OnDestroy, OnInit, SimpleChanges } from '@angular/core';
import { HenkiloListErrorDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';
import { Observable, Subscription } from 'rxjs';
import { KoodistoEnum, VardaKoodistoService } from 'varda-shared';

@Component({
  selector: 'app-varda-form-error-icon',
  templateUrl: './varda-form-error-icon.component.html',
  styleUrls: ['./varda-form-error-icon.component.css']
})
export class VardaFormErrorIconComponent implements OnChanges, OnDestroy {
  @Input() errors: Array<HenkiloListErrorDTO>;
  errorTitle: string;
  subscriptions: Array<Subscription> = [];
  constructor(private koodistoService: VardaKoodistoService) { }

  ngOnChanges(changes: SimpleChanges): void {
    if (this.errors?.length) {
      this.subscriptions.push(
        this.koodistoService.getCodeValueFromKoodisto(KoodistoEnum.virhe, this.errors[0].error_code).subscribe(codeValue => {
          this.errorTitle = codeValue.name;
        })
      );
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
}
