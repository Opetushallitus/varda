import { Injectable } from '@angular/core';
import {Observable, Subject, throwError as observableThrowError} from 'rxjs';
import * as moment_ from 'moment';
const moment = moment_;
import {HttpService} from './http.service';
import {catchError, map} from 'rxjs/operators';
import {CookieService} from 'ngx-cookie-service';
import {VardaUserDTO} from './dto/user-dto';

@Injectable({
  providedIn: 'root'
})
export class LoginService {
  validApiToken = false;

  isValidApiTokenSubject = new Subject<boolean>();
  logoutSubject = new Subject<boolean>();
  fetchedApiTokenSubject = new Subject<boolean>();

  loggedInUserUsername: string;
  loggedInUserEmail: string;

  private _currentUserInfo: VardaUserDTO;

  constructor(private http: HttpService,
              private cookieService: CookieService) { }

  getUsername(): string {
    return this.loggedInUserUsername;
  }

  setUsername(username: string): void {
    this.loggedInUserUsername = username;
  }

  getUserEmail(): string {
    return this.loggedInUserEmail;
  }

  setUserEmail(email: string): void {
    this.loggedInUserEmail = email;
  }

  get currentUserInfo(): VardaUserDTO {
    return this._currentUserInfo || new VardaUserDTO();
  }

  set currentUserInfo(value: VardaUserDTO) {
    this._currentUserInfo = value;
  }

  checkApiTokenValidity(nameSpace: string, apiKeyUrl: string): Observable<boolean> {
    try {
      return new Observable((apiTokenValidityObs) => {
        const tokenData = localStorage.getItem(`${nameSpace}.api.token`);
        if (!tokenData) {
          this.isValidApiTokenSubject.next(false);
          apiTokenValidityObs.next(false);
          apiTokenValidityObs.complete();
          return;
        }

        const parsedTokenObj = JSON.parse(tokenData);
        const token = parsedTokenObj.token;
        const expiryTime = moment(parsedTokenObj.expiryTime);

        const tokenValid = token && !this.tokenExpired(expiryTime);
        this.http.setApiKey(token);

        if (!tokenValid) {
          this.validApiToken = false;
          this.isValidApiTokenSubject.next(false);
          apiTokenValidityObs.next(false);
          apiTokenValidityObs.complete();
          return;
        }

        this.getApiKey(apiKeyUrl).subscribe(() => {
          this.validApiToken = true;
          this.isValidApiTokenSubject.next(true);
          apiTokenValidityObs.next(true);
          apiTokenValidityObs.complete();
        }, () => {
          this.validApiToken = false;
          this.isValidApiTokenSubject.next(false);
          apiTokenValidityObs.next(false);
          apiTokenValidityObs.complete();
        });
      });
    } catch (e) {
      console.log(e);
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
          localStorage.setItem(`${nameSpace}.api.token`, JSON.stringify(authObj));
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

  logout(appUrl: string, nameSpace: string): void {
    this.validApiToken = false;
    localStorage.removeItem(`${nameSpace}.activeToimipaikka`);
    localStorage.removeItem(`${nameSpace}.api.token`);
    localStorage.removeItem(`${nameSpace}.selectedvakajarjestaja`);
    this.loggedInUserUsername = null;
    this.loggedInUserEmail = null;
    setTimeout(() => {
      this.logoutSubject.next(true);
    });
    this.httpLogout(appUrl).subscribe(() => {}, (e) => console.log(e));
  }

  isLoggedOut(): Observable<any> {
    return this.logoutSubject.asObservable();
  }

  private httpLogout(appUrl: string): Observable<any> {
    return this.http.get(appUrl + '/api-auth/logout/').pipe(map((resp: any) => {
      return resp;
    }), catchError((e) => {
      return observableThrowError(e);
    }));
  }

  private refreshApiToken(apiKeyUrl): Observable<any> {
    return this.http.post(apiKeyUrl, {refresh_token: true});
  }

  private checkApiKey(apiKeyUrl: string): Observable<any> {
    return this.http.options(apiKeyUrl);
  }

  private getApiKey(apiKeyUrl: string): Observable<any> {
    return this.http.get(apiKeyUrl);
  }
}
