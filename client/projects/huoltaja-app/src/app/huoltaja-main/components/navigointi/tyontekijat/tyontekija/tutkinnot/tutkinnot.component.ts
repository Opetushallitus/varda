import { Component, Input } from '@angular/core';
import { TutkintoDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/tyontekija-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { KoodistoEnum } from 'varda-shared';

@Component({
  selector: 'app-tutkinnot',
  templateUrl: './tutkinnot.component.html',
  styleUrls: ['./tutkinnot.component.css']
})
export class TutkinnotComponent {
  @Input() tutkinnot: Array<TutkintoDTO>;
  i18n = HuoltajaTranslations;
  koodistoEnum = KoodistoEnum;

  constructor() { }

}
