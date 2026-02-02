import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, Router } from '@angular/router';
import { Observable, of, Subject, Subscriber, throwError } from 'rxjs';
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
  firstLogin = true;

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

    return new Observable(authGuardObs => {
      this.login.checkApiTokenValidity('varda', environment.vardaApiKeyUrl).subscribe((isValid) => {
        if (isValid) {
          canActivate = this.checkLogin(url);
          return this.completeLogin(authGuardObs, canActivate);
        }

        this.casLoginSubject.asObservable().subscribe(() => {
          if (!this.login.validApiToken && environment.production) {
            this.vardaApiService.isLoggedInToCas().subscribe(() => window.location.href = this.getLoginUrl());
          }
        });

        this.login.fetchedApiToken().subscribe(fetchedNewApiToken => {
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

    // If logged in for the first time, get Organisaatio objects
    // (this function is also called when selected Organisaatio changes)
    const firsObservable = this.firstLogin ? this.vakajarjestajaApiService.getVakajarjestajat() : of(undefined);
    this.firstLogin = false;

    firsObservable.pipe(
      switchMap(vakajarjestajaData => {
        if (vakajarjestajaData !== undefined) {
          // Only handle Organisaatio data if it was fetched
          if (!vakajarjestajaData?.length) {
            return throwError(() => ({ noAccess: 'missing oph-kayttooikeudet' }));
          }
          this.vakajarjestajaService.setVakajarjestajat(vakajarjestajaData);
        }
        return this.vakajarjestajaService.listenSelectedVakajarjestaja();
      }),
      switchMap(selectedOrganisaatio =>
        // Set active Organisaatio for user depending on selected Organisaatio
        this.vakajarjestajaApiService.setActiveOrganisaatio(selectedOrganisaatio.id)
      ),
      // Get User data after active Organisaatio has been set (permissions are different)
      switchMap(() => this.vardaApiService.getUserData()),
      switchMap(userData => {
        this.login.setCurrentUser(userData);
        // can throw isPalvelukayttaja-error
        return this.authService.setPermissions(userData);
      }),
      switchMap(() =>
        this.vakajarjestajaApiService.getToimipaikat(this.vakajarjestajaService.getSelectedVakajarjestaja().id)
      ),
      take(1)
    ).subscribe({
      next: toimipaikkaData => {
        this.vakajarjestajaService.setToimipaikat(toimipaikkaData);
        authObserver.next(true);
        authObserver.complete();
      },
      error: err => {
        // redirect errors to our login-failed page
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
