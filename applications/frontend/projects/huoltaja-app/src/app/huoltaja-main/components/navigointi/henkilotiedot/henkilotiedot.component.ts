import { Component, Input } from '@angular/core';
import { HuoltajaApiService } from 'projects/huoltaja-app/src/app/services/huoltaja-api.service';
import { HenkilotiedotDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/henkilo-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { Observable } from 'rxjs';
import { KoodistoEnum } from 'varda-shared';

@Component({
    selector: 'app-henkilotiedot',
    templateUrl: './henkilotiedot.component.html',
    styleUrls: ['./henkilotiedot.component.css'],
    standalone: false
})
export class HenkilotiedotComponent {
  @Input() hideSyntymaPvm = false;

  henkilotiedot$: Observable<HenkilotiedotDTO>;
  i18n = HuoltajaTranslations;
  koodistoEnum = KoodistoEnum;

  constructor(private huoltajaApiService: HuoltajaApiService) {
    this.henkilotiedot$ = this.huoltajaApiService.getHenkilotiedot();
  }
}
