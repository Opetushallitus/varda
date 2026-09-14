import {Component, Input } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

@Component({
    selector: 'app-varda-toggle-button',
    templateUrl: './varda-toggle-button.component.html',
    styleUrls: ['./varda-toggle-button.component.css'],
    standalone: false
})
export class VardaToggleButtonComponent {
  // Is show or hide button displayed
  @Input() isUp: boolean;
  @Input() showTextKey: string;
  @Input() hideTextKey: string;

  i18n = VirkailijaTranslations;

  constructor() { }
}
