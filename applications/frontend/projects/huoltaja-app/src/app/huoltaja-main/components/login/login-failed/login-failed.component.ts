import { Component } from '@angular/core';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';

@Component({
    selector: 'app-login-failed',
    templateUrl: './login-failed.component.html',
    styleUrls: ['./login-failed.component.css', '../login.component.css'],
    standalone: false
})
export class LoginFailedComponent {
  i18n = HuoltajaTranslations;
  originLink: string = window.origin;
  constructor() { }

}
