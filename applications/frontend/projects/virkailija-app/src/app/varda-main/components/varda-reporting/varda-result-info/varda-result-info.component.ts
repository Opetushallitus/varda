import { Component, Input } from '@angular/core';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';

@Component({
    selector: 'app-varda-result-info',
    templateUrl: './varda-result-info.component.html',
    styleUrls: ['./varda-result-info.component.css'],
    standalone: false
})
export class VardaResultInfoComponent {
  @Input() resultCount: number;
  @Input() filterString: string;

  i18n = VirkailijaTranslations;

  constructor() { }
}
