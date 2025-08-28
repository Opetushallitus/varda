import { Component, Input } from '@angular/core';
import { TyoskentelypaikkaDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/tyontekija-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { KoodistoEnum } from 'varda-shared';

@Component({
  selector: 'app-tyoskentelypaikka',
  templateUrl: './tyoskentelypaikka.component.html',
  styleUrls: ['./tyoskentelypaikka.component.css']
})
export class TyoskentelypaikkaComponent {
  @Input() tyoskentelypaikka: TyoskentelypaikkaDTO;
  i18n = HuoltajaTranslations;
  koodistoEnum = KoodistoEnum;
  expanded: boolean;

  constructor() { }

  togglePanel(expand: boolean) {
    this.expanded = expand;
  }
}
