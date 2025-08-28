import { Component } from '@angular/core';
import { PublicTranslations } from '../../../assets/i18n/translations.enum';

@Component({
  selector: 'app-public-not-found',
  templateUrl: './public-not-found.component.html',
  styleUrls: ['./public-not-found.component.css']
})
export class PublicNotFoundComponent {
  translation = PublicTranslations;

  constructor() { }
}
