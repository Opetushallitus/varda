/* eslint-disable @typescript-eslint/no-unused-vars */
import { TestBed } from '@angular/core/testing';

import { LoginService } from './login.service';
import { DateTime } from 'luxon';
import {EMPTY} from 'rxjs';
import {HttpService} from './http.service';
import {CookieService} from 'ngx-cookie-service';
import { MatSnackBar } from '@angular/material/snack-bar';

describe('LoginService', () => {
  let sessionStorageGetItemSpy;
  let loginService;
  let validTokenObj;
  let expiredTokenObj;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        LoginService,
        CookieService,
        { provide: MatSnackBar, useValue: EMPTY },
        {
          provide: HttpService,
          useValue: {
            apiKey: '',
            setApiKey: () => {},
            get: () => EMPTY,
            options: () => EMPTY
          }
        }
        ]
    });
    loginService = TestBed.inject<LoginService>(LoginService);
    validTokenObj = JSON.stringify({token: '123918687ec3462b4a35d0c5c6da0dbeedf3', expiryTime: loginService.createExpiryTime()});
    expiredTokenObj = JSON.stringify(
      {token: '123afdasfdsadf2b4a35d0c5c6da0dbeedf3',expiryTime: DateTime.now().minus({ days: 1 }).toISO()}
    );
  });

  it('should be created', () => {
    expect(loginService).toBeTruthy();
  });

  it('Should return true for loggedIn status if token exists and is not expired', () => {
    sessionStorageGetItemSpy = spyOn(sessionStorage, 'getItem').and.returnValue(validTokenObj);
    loginService.checkApiTokenValidity('huoltaja', '/').subscribe((d) => {
      const isLoggedIn = d;
      expect(isLoggedIn).toBeTruthy();
    });
  });

  it('Should return false for loggedIn status if token is expired', () => {
    sessionStorageGetItemSpy = spyOn(sessionStorage, 'getItem').and.returnValue(expiredTokenObj);
    loginService.checkApiTokenValidity('huoltaja', '/').subscribe((d) => {
      const isLoggedIn = d;
      expect(isLoggedIn).toBeFalsy();
    });
  });

  it('Should return true if token expirytime is in the past', () => {
    const yesterday = DateTime.now().minus({ days: 1 });
    const twoWeeksAgo = DateTime.now().minus({ days: 14 });

    const res1 = loginService.tokenExpired(yesterday);
    const res2 = loginService.tokenExpired(twoWeeksAgo);

    expect(res1).toBeTruthy();
    expect(res2).toBeTruthy();
  });

  it('Should return false if token expirytime is in the future', () => {
    const oneMinuteLater = DateTime.now().plus({ minutes: 1 });
    const tomorrow = DateTime.now().plus({ days: 1 });

    const res1 = loginService.tokenExpired(oneMinuteLater);
    const res2 = loginService.tokenExpired(tomorrow);

    expect(res1).toBeFalsy();
    expect(res2).toBeFalsy();
  });

});
