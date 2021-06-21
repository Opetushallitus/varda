import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import * as moment_ from 'moment';
const moment = moment_;
import { HttpService } from './http.service';
import { CookieService } from 'ngx-cookie-service';
import { VardaUserDTO } from './models/user-dto';
import { TranslateService } from '@ngx-translate/core';
import { MatSnackBar, MatSnackBarRef } from '@angular/material/snack-bar';
import { take } from 'rxjs/operators';
import { TimeoutTranslationKey, LoginTimeoutComponent } from './components/login-timeout/login-timeout.component';

@Injectable({
  providedIn: 'root'
})
export class LoginService {
  validApiToken = false;
  isValidApiTokenSubject = new Subject<boolean>();
  logoutSubject = new Subject<boolean>();
  fetchedApiTokenSubject = new Subject<boolean>();
  private currentUser$ = new BehaviorSubject<VardaUserDTO>(null);
  private sessionTimeoutTimer: ReturnType<typeof setTimeout>;
  private timeoutSettings: {
    timeout: number;
    translate: TranslateService;
    logoutURL: string;
    lifetimeSeconds: number;
  };

  private snackBarRef: MatSnackBarRef<any>;

  constructor(
    private http: HttpService,
    private cookieService: CookieService,
    private snackbar: MatSnackBar
  ) { }


  getCurrentUser(): Observable<VardaUserDTO> {
    return this.currentUser$.asObservable();
  }

  setCurrentUser(userData: VardaUserDTO): void {
    this.currentUser$.next(userData);

  }

  checkApiTokenValidity(nameSpace: string, apiKeyUrl: string): Observable<boolean> {
    try {
      return new Observable((apiTokenValidityObs) => {
        const completeObs = (isValidToken: boolean) => {
          this.validApiToken = isValidToken;
          this.isValidApiTokenSubject.next(isValidToken);
          apiTokenValidityObs.next(isValidToken);
          apiTokenValidityObs.complete();
        };

        const tokenData = sessionStorage.getItem(`${nameSpace}.api.token`);
        if (!tokenData) {
          return completeObs(false);
        }

        const parsedTokenObj = JSON.parse(tokenData);
        const token = parsedTokenObj.token;
        const expiryTime = moment(parsedTokenObj.expiryTime);

        const tokenValid = token && !this.tokenExpired(expiryTime);
        this.http.setApiKey(token);

        if (!tokenValid) {
          return completeObs(false);
        }

        this.getApiKey(apiKeyUrl).subscribe({
          next: () => completeObs(true),
          error: err => completeObs(false)
        });
      });
    } catch (err) {
      console.log(err);
    }
    return;
  }

  fetchedApiToken(): Observable<boolean> {
    return this.fetchedApiTokenSubject.asObservable();
  }

  tokenExpired(expiryTime: moment_.Moment): boolean {
    const now = moment();
    return now.isAfter(expiryTime);
  }

  createExpiryTime(): moment_.Moment {
    const now = moment();
    return now.add(12, 'h');
  }

  getApiTokenFromCookie(nameSpace: string, apiKeyUrl: string): Promise<string> {
    return new Promise<string>((resolve, reject) => {
      const token = this.cookieService.get('token');
      if (token) {
        this.http.setApiKey(token);
        this.refreshApiToken(apiKeyUrl).subscribe((tokenObj) => {
          const newToken = tokenObj.token;
          this.validApiToken = true;
          const authObj = {
            token: newToken,
            expiryTime: this.createExpiryTime()
          };
          this.http.setApiKey(newToken);
          sessionStorage.setItem(`${nameSpace}.api.token`, JSON.stringify(authObj));
          this.fetchedApiTokenSubject.next(true);
          resolve(newToken);
        }, (error) => {
          this.fetchedApiTokenSubject.next(false);
          resolve(token);
        });
      } else {
        this.fetchedApiTokenSubject.next(false);
        resolve(token);
      }
    });
  }

  isValidApiToken(): Observable<boolean> {
    return this.isValidApiTokenSubject.asObservable();
  }

  initBroadcastChannel(apiToken: string) {
    if ('BroadcastChannel' in self) {
      const originalRoute = window.location.pathname;
      const [requestToken, sendToken] = ['requestToken', 'sendToken'];
      const channel = new BroadcastChannel(apiToken);
      channel.onmessage = (e) => {
        const token = sessionStorage.getItem(apiToken);
        if (token && e.data.action === requestToken) {
          channel.postMessage({ action: sendToken, token });
        } else if (!token && e.data.action === sendToken) {
          sessionStorage.setItem(apiToken, e.data.token);
          window.location.href = originalRoute;
        }
      };

      channel.postMessage({ action: requestToken });
    }
  }

  initLogoutInterval(seconds: number, translate: TranslateService, logoutURL: string) {
    this.timeoutSettings = {
      timeout: seconds * 1000,
      translate,
      logoutURL,
      lifetimeSeconds: 180
    };
    this.clearLogoutInterval();
  }

  clearLogoutInterval() {
    if (this.timeoutSettings) {
      clearTimeout(this.sessionTimeoutTimer);
      this.sessionTimeoutTimer = setTimeout(() => this.showLogoutPopup(), this.timeoutSettings.timeout);
    }
  }

  initTokenExpired() {
    clearTimeout(this.sessionTimeoutTimer);

    if (!this.snackBarRef) {
      this.timeoutSettings.translate.get([
        TimeoutTranslationKey.timeout_expired_text,
        TimeoutTranslationKey.timeout_expired_close_seconds_COUNT,
        TimeoutTranslationKey.timeout_expired_action_text
      ]).subscribe(translations => {
        const logoutTimer = setTimeout(() => window.location.reload(), this.timeoutSettings.lifetimeSeconds * 1000);
        this.snackBarRef = this.snackbar.openFromComponent(LoginTimeoutComponent, {
          data: {
            reasonText: translations[TimeoutTranslationKey.timeout_expired_text],
            counterText: translations[TimeoutTranslationKey.timeout_expired_close_seconds_COUNT],
            actionText: translations[TimeoutTranslationKey.timeout_expired_action_text],
            seconds: this.timeoutSettings.lifetimeSeconds,
            dismiss: () => {
              clearTimeout(logoutTimer);
              this.snackBarRef.dismiss();
            }
          },
          duration: this.timeoutSettings.lifetimeSeconds * 1000 + 1000
        });
      });
    }

  }

  private showLogoutPopup() {
    if (!this.snackBarRef) {
      this.timeoutSettings.translate.get([
        TimeoutTranslationKey.timeout_inactive_text,
        TimeoutTranslationKey.timeout_logout_seconds_COUNT,
        TimeoutTranslationKey.timeout_action_text
      ]).subscribe(translations => {
        const logoutTimer = setTimeout(() =>
          window.location.origin.includes('opintopolku') ? window.location.href = this.timeoutSettings.logoutURL : window.location.reload(),
          this.timeoutSettings.lifetimeSeconds * 1000);
        this.snackBarRef = this.snackbar.openFromComponent(LoginTimeoutComponent, {
          data: {
            reasonText: translations[TimeoutTranslationKey.timeout_inactive_text],
            counterText: translations[TimeoutTranslationKey.timeout_logout_seconds_COUNT],
            actionText: translations[TimeoutTranslationKey.timeout_action_text],
            seconds: this.timeoutSettings.lifetimeSeconds,
            dismiss: () => {
              clearTimeout(logoutTimer);
              this.snackBarRef.dismiss();
            }
          },
          duration: this.timeoutSettings.lifetimeSeconds * 1000 + 1000
        });

        this.snackBarRef.afterDismissed().pipe(take(1)).subscribe(() => this.snackBarRef = null);
      });
    }
  }

  private refreshApiToken(apiKeyUrl): Observable<any> {
    return this.http.post(apiKeyUrl, { refresh_token: true });
  }

  private getApiKey(apiKeyUrl: string): Observable<any> {
    return this.http.get(apiKeyUrl);
  }
}
