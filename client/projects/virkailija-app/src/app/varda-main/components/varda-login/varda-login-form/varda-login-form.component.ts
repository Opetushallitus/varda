import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { environment } from '../../../../../environments/environment';
import { LoginService } from 'varda-shared';

@Component({
  selector: 'app-varda-login-form',
  templateUrl: './varda-login-form.component.html',
  styleUrls: ['./varda-login-form.component.css']
})
export class VardaLoginFormComponent implements OnInit {

  next = encodeURIComponent(environment.vardaFrontendUrl + '/');
  vardaBackendLoginUrl = `${environment.vardaAppUrl}/accounts/login?next=${this.next}`;
  showLogOutMsg = false;
  tokenInput = {
    show: !environment.production && environment.vardaFrontendUrl === 'http://localhost:4200',
    value: null,
    backend: environment.vardaApiKeyUrl
  };


  constructor(
    private loginService: LoginService,
    private router: Router) {
    this.loginService.isLoggedOut().subscribe((isLoggedOut: boolean) => {
      this.showLogOutMsg = isLoggedOut;
    });
  }

  navigateToVardaLogin(): void {
    window.location.href = this.vardaBackendLoginUrl;
  }

  addLoginToken(token: string): void {
    const today = new Date();
    today.setMonth(today.getMonth() + 2);

    localStorage.setItem('varda.api.token', JSON.stringify({
      token: token,
      expiryTime: today.toISOString()
    }));
    this.router.navigate(['/']);
  }

  ngOnInit() {
    if (this.loginService.isValidApiToken()) {
      this.router.navigate(['/']);
    }
  }
}
