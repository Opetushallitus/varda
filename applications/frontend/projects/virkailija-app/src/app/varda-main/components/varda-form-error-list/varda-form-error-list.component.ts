import { Component, Input } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { KoodistoEnum } from 'varda-shared';
import { PuutteellinenErrorDTO } from '../../../utilities/models/dto/varda-puutteellinen-dto.model';

@Component({
    selector: 'app-varda-form-error-list',
    templateUrl: './varda-form-error-list.component.html',
    styleUrls: ['./varda-form-error-list.component.css'],
    standalone: false
})
export class VardaFormErrorListComponent {
  @Input() errors: Array<PuutteellinenErrorDTO>;
  koodistoEnum = KoodistoEnum;
  i18n = VirkailijaTranslations;

  constructor() { }
}
