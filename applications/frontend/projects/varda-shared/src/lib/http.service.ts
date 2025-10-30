/* eslint-disable @typescript-eslint/no-unused-vars */
import { Injectable } from '@angular/core';
import { Observable, of, throwError, throwError as observableThrowError, BehaviorSubject, EMPTY } from 'rxjs';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { catchError, delay, map, retryWhen, take, expand, reduce, mergeMap } from 'rxjs/operators';

export abstract class AbstractHttpService {
  public apiKey = '';
  private apiKey$ = new BehaviorSubject<string>(null);
  private _http;

  constructor(http: HttpClient) {
    this._http = http;
  }

  setApiKey(token: string): void {
    this.apiKey = token;
    this.apiKey$.next(token);
  }

  getApiKey(): Observable<string> {
    return this.apiKey$.asObservable();
  }


  getWithCallerId(url: string, options?: any): Observable<any> {
    const httpHeadersCallerId = new HttpHeaders({ 'Caller-Id': 'csc.varda' });
    return this.get(url, options, httpHeadersCallerId);
  }

  generateRandomInterval(min: number, max: number) {
    return Math.floor(Math.random() * (max - min + 1) + min);
  }

  getApiKeyByVardaCredentials(username: string, password: string, apiKeyPath: string): Observable<any> {
    const credentialsStr = `${username}:${password}`;
    const authStr = ` Basic ${this.base64encode(credentialsStr)}`;
    const httpHeaders = new HttpHeaders({ Authorization: authStr });
    return this._http.get(apiKeyPath, { headers: httpHeaders }).pipe(map((resp: any) => {
      const respBody = resp;
      this.setApiKey(resp.token);
      return respBody;
    }), catchError(e => e.json()));
  }

  base64encode(str: string): string {
    return btoa(str);
  }

  httpRetry(maxRetry = 10, minDelayMs = 2000, maxDelayMs = 3000) {
    return (src: Observable<any>) => src.pipe(
      retryWhen(errors => {
        const randomInterval = this.generateRandomInterval(minDelayMs, maxDelayMs);
        return errors.pipe(
          mergeMap(error => error.status === 429 ? of(error) : throwError(error)),
          delay(randomInterval),
          take(maxRetry)
        );
      })
    );
  }

  abstract get(url: string, options?: any, httpHeadersParam?: HttpHeaders): Observable<any>;
  abstract getAllResults(url: string, backendUrl: string, options?: any): Observable<Array<any>>;
  abstract post(url: string, formData: any, options?: any): Observable<any>;
  abstract put(url: string, formData: any, options?: any): Observable<any>;
  abstract patch(url: string, formData: any, options?: any): Observable<any>;
  abstract options(url: string, options?: any): Observable<any>;
  abstract delete(url: string, options?: any): Observable<any>;
}

@Injectable({
  providedIn: 'root'
})
export class HttpService extends AbstractHttpService {

  constructor(private http: HttpClient) {
    super(http);
  }

  get(url: string, urlParams?: any, httpHeadersParam?: HttpHeaders, options?: any): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = httpHeadersParam || new HttpHeaders({ Authorization: authToken });
    const params = new HttpParams({
      fromObject: urlParams,
    });
    return this.http.get(url, { headers: httpHeaders, params, ...options })
      .pipe(
        this.httpRetry(),
        map((resp: any) => resp),
        catchError((e) => observableThrowError(e))
      );
  }

  getAllResults(url: string, backendUrl: string, options?: any): Observable<Array<any>> {

    const nextLink = (nextUrl: string): Observable<any> => {
      try { // check if url is valid
        const properUrl = new URL(nextUrl);
      } catch (e) { // if not presume its /api/something
        nextUrl = `${backendUrl}${nextUrl}`;
      }

      return this.get(nextUrl);
    };

    return this.get(url, options).pipe(
      expand((res: any) => res.next ? nextLink(res.next) : EMPTY),
      reduce((acc, res: any) => acc.concat(res.results), [])
    );
  }

  post(url: string, formData: any, options?: any): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = new HttpHeaders({ Authorization: authToken });
    return this.http.post(
      url, formData, { headers: httpHeaders }).pipe(map((resp: any) => resp), catchError((e) => observableThrowError(e))
    );
  }

  put(url: string, formData: any, options?: any): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = new HttpHeaders({ Authorization: authToken });
    return this.http.put(
      url, formData, { headers: httpHeaders }).pipe(map((resp: any) => resp), catchError((e) => observableThrowError(e))
    );
  }

  patch(url: string, formData: any, options?: any): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = new HttpHeaders({ Authorization: authToken });
    return this.http.patch(
      url, formData, { headers: httpHeaders }).pipe(map((resp: any) => resp), catchError((e) => observableThrowError(e))
    );
  }

  options(url: string, options?: any): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = new HttpHeaders({ Authorization: authToken });
    return this.http.options(url, { headers: httpHeaders }).pipe(map((resp: any) => resp), catchError((e) => observableThrowError(e)));
  }

  delete(url: string, options?: any): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = new HttpHeaders({ Authorization: authToken });
    return this.http.delete(url, { headers: httpHeaders }).pipe(map((resp: any) => resp), catchError((e) => observableThrowError(e)));
  }

}
