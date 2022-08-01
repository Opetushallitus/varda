import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, Router } from '@angular/router';
import { Observable, Subject, Subscriber, throwError } from 'rxjs';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';
import { LoginService } from 'varda-shared';
import { VardaApiService } from '../services/varda-api.service';
import { VardaVakajarjestajaApiService } from '../services/varda-vakajarjestaja-api.service';
import { VardaVakajarjestajaService } from '../services/varda-vakajarjestaja.service';
import { switchMap, take } from 'rxjs/operators';

const loginRoute = '/login';
const loginFailedRoute = '/login-failed';

export enum LoginErrorType {
  palvelukayttaja = 'palvelukayttaja',
  noAccess = 'no-access',
  unknown = 'error',
}

@Injectable()
export class AuthGuard implements CanActivate {

  casLoginSubject = new Subject<boolean>();

  constructor(
    private authService: AuthService,
    private router: Router,
    private login: LoginService,
    private vardaApiService: VardaApiService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private vakajarjestajaService: VardaVakajarjestajaService,
  ) { }

  canActivate(next: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean> | Promise<boolean> | boolean {
    const url = state.url;
    let canActivate: boolean;

    return new Observable((authGuardObs) => {
      this.login.checkApiTokenValidity('varda', environment.vardaApiKeyUrl).subscribe((isValid) => {
        if (isValid) {
          canActivate = this.checkLogin(url);
          return this.completeLogin(authGuardObs, canActivate);
        }

        this.casLoginSubject.asObservable().subscribe((data) => {
          if (!this.login.validApiToken && environment.production) {
            this.vardaApiService.isLoggedInToCas().subscribe(() => window.location.href = this.getLoginUrl());
          }
        });

        this.login.fetchedApiToken().subscribe((fetchedNewApiToken) => {
          this.checkLogin(url);
          this.completeLogin(authGuardObs, fetchedNewApiToken);
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
    this.authService.redirectUrl = url;
    this.router.navigate([loginRoute]);
    return false;
  }

  completeLogin(authObserver: Subscriber<boolean>, isLoggedIn: boolean) {
    if (!isLoggedIn) {
      authObserver.next(false);
      authObserver.complete();
      return this.router.navigate([loginRoute]);
    }


    this.vardaApiService.getUserData().pipe( // get userData to see if you are logged in to opintopolku
      switchMap(userData => {
        this.login.setCurrentUser(userData);
        return this.authService.setPermissions(userData); // can throw isPalvelukayttaja-error
      }),
      // get list of vakajarjestajat
      switchMap(() => this.vakajarjestajaApiService.getVakajarjestajat()),
      switchMap(vakajarjestajat => { // if vakajarjestajat list is empty presume user is missing oph-kayttooikeudet
        if (!vakajarjestajat?.length) {
          return throwError({ noAccess: 'missing oph-kayttooikeudet' });
        }
        this.vakajarjestajaService.setVakajarjestajat(vakajarjestajat);
        return this.vakajarjestajaService.listenSelectedVakajarjestaja();
      }),
      // getToimipaikat ALWAYS returns toimipaikat[]
      switchMap(vakajarjestaja => this.vakajarjestajaApiService.getToimipaikat(vakajarjestaja.id)),
      take(1)
    ).subscribe({
      next: toimipaikat => {
        this.vakajarjestajaService.setToimipaikat(toimipaikat);
        this.authService.initUserPermissions();

        authObserver.next(true);
        authObserver.complete();
      }, error: err => { // redirect errors to our login-failed page
        let fragment = LoginErrorType.unknown;
        if (err.isPalvelukayttaja) {
          fragment = LoginErrorType.palvelukayttaja;
        } else if (err.noAccess) {
          fragment = LoginErrorType.noAccess;
        }

        console.error('Login error', err);

        authObserver.next(false);
        authObserver.complete();
        this.router.navigate([loginFailedRoute], { fragment });
      }
    });
  }
}
