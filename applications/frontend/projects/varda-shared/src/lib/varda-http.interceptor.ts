import { Injectable } from '@angular/core';
import { HttpEvent, HttpInterceptor, HttpHandler, HttpRequest, HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, Observable, throwError, timer } from 'rxjs';
import { catchError, filter, mergeMap, take, tap } from 'rxjs/operators';
import { LoginService } from './login.service';

@Injectable()
export class VardaHttpInterceptor implements HttpInterceptor {
  private readonly timeFrame = 1000;
  private availableThreads = 15;
  private rateLimit$ = new BehaviorSubject(this.availableThreads);
  private lastAuthFailed = 0;

  private authenticationErrorsList = ['PE007'];
  constructor(private loginService: LoginService) { }

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    this.loginService.clearLogoutInterval();

    return this.rateLimit$.pipe(
      filter(() => this.availableThreads > 0),
      take(1),
      tap(() => this.removeThreads()),
      tap(() => timer(this.timeFrame).subscribe(() => this.addThreads())),
      mergeMap(() => next.handle(req).pipe(
        catchError((err: HttpErrorResponse) => {
          const authenticationError = err?.error?.errors?.find((errorLine) => this.authenticationErrorsList.includes(errorLine.error_code));
          if (authenticationError && Date.now() - this.lastAuthFailed > 15000) {
            this.lastAuthFailed = Date.now();
            this.loginService.initTokenExpired();
          }
          return throwError(err);
        })))
    );
  }

  private addThreads(): void {
    this.changeThreads(1);
  }

  private removeThreads(): void {
    this.changeThreads(-1);
  }

  private changeThreads(value: number): void {
    this.rateLimit$.next(this.availableThreads += value);
  }
}
