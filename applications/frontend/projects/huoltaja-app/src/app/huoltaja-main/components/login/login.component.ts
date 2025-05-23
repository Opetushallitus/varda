import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { environment } from 'projects/huoltaja-app/src/environments/environment';
import { HuoltajaCookieEnum } from '../../../utilities/models/enum/huoltaja-cookie.enum';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  i18n = HuoltajaTranslations;
  loginURL = `${environment.huoltajaBackendUrl}/accounts/huoltaja-login?next=/varda/`;
  tokenInput = {
    show: !environment.production && environment.huoltajaFrontendUrl === 'http://localhost:4200',
    value: null,
    backend: `${environment.huoltajaBackendUrl}/api/user/apikey/`
  };

  constructor(private router: Router) { }

  addLoginToken(token: string): void {
    const today = new Date();
    today.setMonth(today.getMonth() + 2);

    sessionStorage.setItem(HuoltajaCookieEnum.api_token, JSON.stringify({
      token,
      expiryTime: today.toISOString()
    }));
    this.router.navigate(['/']);
  }
}
