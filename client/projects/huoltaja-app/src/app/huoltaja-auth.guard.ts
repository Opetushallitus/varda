import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, UrlTree } from '@angular/router';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';
import { LoginService, SupportedLanguage, VardaKoodistoService } from 'varda-shared';
import { HuoltajaApiService } from './services/huoltaja-api.service';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';

const loginRoute = '/login';
const loginFailedRoute = '/login-failed';

@Injectable({
  providedIn: 'root'
})
export class HuoltajaAuthGuard implements CanActivate {
  constructor(
    private loginService: LoginService,
    private apiService: HuoltajaApiService,
    private koodistoService: VardaKoodistoService,
    private translateService: TranslateService,
    private router: Router
  ) { }

  canActivate(
    next: ActivatedRouteSnapshot,
    state: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return new Observable((authGuardObs) => {
      const url = `${environment.huoltajaBackendUrl}/api/user/apikey/`;

      this.loginService.getApiTokenFromCookie('huoltaja', url).then(newToken => {
        this.loginService.checkApiTokenValidity('huoltaja', url).subscribe((isValid) => {
          if (!isValid) {
            // Redirect to login
            this.router.navigate([loginRoute]);
            authGuardObs.next(false);
            authGuardObs.complete();
          } else {
            // Save userdata
            this.apiService.getUserInfo().subscribe({
              next: userdata => {
                this.loginService.setCurrentUser(userdata);
                this.koodistoService.initKoodistot(environment.huoltajaBackendUrl, this.translateService.currentLang as SupportedLanguage);
                authGuardObs.next(true);
                authGuardObs.complete();
              }, error: err => {
                console.error('getUser Error', err);
                this.router.navigate([loginFailedRoute]);
                authGuardObs.next(false);
                authGuardObs.complete();
              }
            });
          }
        });
      });
    });
  }
}
