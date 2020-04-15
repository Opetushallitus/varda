import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, UrlTree } from '@angular/router';
import { Observable } from 'rxjs';
import {environment} from '../environments/environment';
import {LoginService} from 'varda-shared';
import {HuoltajaApiService} from './services/huoltaja-api.service';
import { Router} from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class HuoltajaAuthGuard implements CanActivate {
  constructor(private loginService: LoginService,
              private apiService: HuoltajaApiService,
              private router: Router) {}

  canActivate(
    next: ActivatedRouteSnapshot,
    state: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return new Observable((authGuardObs) => {
      const url = `${environment.huoltajaAppUrl}/api/user/apikey/`;
      // Check if we have already token cookie and refresh the token
      this.loginService.getApiTokenFromCookie('huoltaja', url).then(newToken => {
        this.loginService.checkApiTokenValidity('huoltaja', url).subscribe((isValid) => {
          if (!isValid) {
            // Redirect to login
            if (environment.production) {
              window.location.href = this.getLoginUrl();
            } else {
              console.log('You are in dev mode. Set localstorage "huoltaja.api.token" manually. This is because CSRF protection is ' +
                'preventing our token cookie catching from other domain. See README for more details..');
            }
            authGuardObs.next(false);
            authGuardObs.complete();
          } else {
            // Save userdata
            this.apiService.getUserInfo().subscribe(userdata => {
              this.loginService.currentUserInfo = userdata;
              if (!userdata.henkilo_oid) {
                // TODO: palauta kun CAS palauttaa oikeita tietoja
                // authGuardObs.next(this.router.parseUrl('/ei-oikeuksia'));
              }
              authGuardObs.next(true);
              authGuardObs.complete();
            });
          }
        });
      });
    });
  }

  private getLoginUrl(): string {
    const next = encodeURIComponent(environment.huoltajaFrontendUrl + '/');
    return `${environment.huoltajaAppUrl}/accounts/huoltaja-login?next=${next}`;
  }

}
