import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { environment } from '../../../../../environments/environment';
import { LoginService } from 'varda-shared';
import { BehaviorSubject } from 'rxjs';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-varda-login-form',
  templateUrl: './varda-login-form.component.html',
  styleUrls: ['./varda-login-form.component.css']
})
export class VardaLoginFormComponent implements OnInit {
  isLoading = new BehaviorSubject<boolean>(false);
  next = encodeURIComponent(environment.vardaFrontendUrl + '/');
  vardaBackendLoginUrl = `${environment.vardaAppUrl}/accounts/login?next=${this.next}`;
  tokenInput = {
    show: !environment.production && environment.vardaFrontendUrl === 'http://localhost:4200',
    value: null,
    backend: environment.vardaApiKeyUrl
  };

  constructor(
    private loginService: LoginService,
    private router: Router
  ) {

  }

  navigateToVardaLogin(): void {
    this.isLoading.next(true);
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
    this.router.navigate(['/']);

    const loginSub = this.loginService.isValidApiToken().pipe(filter(Boolean)).subscribe((isValid: boolean) => {
      this.router.navigate(['/']);
      loginSub.unsubscribe();
    });
  }
}
