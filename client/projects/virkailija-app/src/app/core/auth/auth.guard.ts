import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, Router } from '@angular/router';
import { Observable, Subject } from 'rxjs';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';
import { LoginService } from 'varda-shared';

@Injectable()
export class AuthGuard implements CanActivate {

  casLoginSubject = new Subject<boolean>();

  constructor(
    private auth: AuthService,
    private router: Router,
    private login: LoginService
  ) { }

  canActivate(next: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean> | Promise<boolean> | boolean {

    const url = state.url;

    let canActivate;

    return new Observable((authGuardObs) => {
      this.login.checkApiTokenValidity('varda', environment.vardaApiKeyUrl).subscribe((isValid) => {
        if (isValid) {
          canActivate = this.checkLogin(url);
          authGuardObs.next(canActivate);
          authGuardObs.complete();
          return;
        }

        this.casLoginSubject.asObservable().subscribe((data) => {
          if (!this.login.validApiToken && environment.production) {
            this.auth.casSessionExists().subscribe(() => {
              window.location.href = this.getLoginUrl();
            }, () => { });
          }
        });

        this.login.fetchedApiToken().subscribe((fetchedNewApiToken) => {
          canActivate = this.checkLogin(url);
          authGuardObs.next(fetchedNewApiToken);
          authGuardObs.complete();
          this.casLoginSubject.next(true);
          this.casLoginSubject.complete();
        });

        this.login.getApiTokenFromCookie('varda', environment.vardaApiKeyUrl);
      });
    });
  }

  getLoginUrl(): string {
    const next = encodeURIComponent(environment.vardaFrontendUrl + '/');
    const vardaBackendLoginUrl = `${environment.vardaAppUrl}/accounts/login?next=${next}`;
    return vardaBackendLoginUrl;
  }

  checkLogin(url: string): boolean {
    if (this.login.validApiToken) {
      return true;
    }
    this.auth.redirectUrl = url;
    this.router.navigate(['/login']);
    return false;
  }

}
