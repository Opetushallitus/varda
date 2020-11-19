import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject, throwError as observableThrowError } from 'rxjs';
import * as moment_ from 'moment';
const moment = moment_;
import { HttpService } from './http.service';
import { CookieService } from 'ngx-cookie-service';
import { VardaUserDTO } from './dto/user-dto';

@Injectable({
  providedIn: 'root'
})
export class LoginService {
  validApiToken = false;

  isValidApiTokenSubject = new Subject<boolean>();
  logoutSubject = new Subject<boolean>();
  fetchedApiTokenSubject = new Subject<boolean>();
  private currentUser$ = new BehaviorSubject<VardaUserDTO>(null);

  constructor(
    private http: HttpService,
    private cookieService: CookieService,
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

        const tokenData = localStorage.getItem(`${nameSpace}.api.token`);
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

  private refreshApiToken(apiKeyUrl): Observable<any> {
    return this.http.post(apiKeyUrl, { refresh_token: true });
  }

  private getApiKey(apiKeyUrl: string): Observable<any> {
    return this.http.get(apiKeyUrl);
  }
}
