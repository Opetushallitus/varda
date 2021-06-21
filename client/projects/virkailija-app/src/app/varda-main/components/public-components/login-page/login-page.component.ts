import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { VardaCookieEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/varda-cookie.enum';
import { environment } from 'projects/virkailija-app/src/environments/environment';
import { BehaviorSubject } from 'rxjs';

@Component({
  selector: 'app-login-page',
  templateUrl: './login-page.component.html',
  styleUrls: ['./login-page.component.css']
})
export class LoginPageComponent implements OnInit {
  isLoading = new BehaviorSubject<boolean>(false);
  next = encodeURIComponent(environment.vardaFrontendUrl + '/');
  vardaBackendLoginUrl = `${environment.vardaAppUrl}/accounts/login?next=${this.next}`;
  tokenInput = {
    show: !environment.production && environment.vardaFrontendUrl === 'http://localhost:4200',
    value: null,
    backend: environment.vardaApiKeyUrl
  };

  constructor(private router: Router) { }

  navigateToVardaLogin(): void {
    this.isLoading.next(true);
    window.location.href = this.vardaBackendLoginUrl;
  }

  addLoginToken(token: string): void {
    const today = new Date();
    today.setMonth(today.getMonth() + 2);

    sessionStorage.setItem(VardaCookieEnum.api_token, JSON.stringify({
      token,
      expiryTime: today.toISOString()
    }));
    this.router.navigate(['/']);
  }

  ngOnInit() {
    this.router.navigate(['/']);
  }
}
