import { Component } from '@angular/core';
import { PulssiTranslations } from '../../../assets/i18n/translations.enum';

@Component({
    selector: 'app-not-found',
    templateUrl: './not-found.component.html',
    styleUrls: ['./not-found.component.css'],
    standalone: false
})
export class NotFoundComponent {
  translations = PulssiTranslations;

  constructor() { }
}
