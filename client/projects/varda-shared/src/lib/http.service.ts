import { Injectable } from '@angular/core';
import { Observable, of, throwError, throwError as observableThrowError, BehaviorSubject } from 'rxjs';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { catchError, delay, flatMap, map, retryWhen, take } from 'rxjs/operators';

export abstract class AbstractHttpService {
  public apiKey = '';
  private apiKey$ = new BehaviorSubject<string>(null);
  private _http;

  constructor(http: HttpClient) {
    this._http = http;
  }

  abstract get(url: string, options?: any, httpHeadersParam?: HttpHeaders): Observable<any>;
  abstract post(url: string, formData: any, options?: any): Observable<any>;
  abstract put(url: string, formData: any, options?: any): Observable<any>;
  abstract patch(url: string, formData: any, options?: any): Observable<any>;
  abstract options(url: string, options?: any): Observable<any>;
  abstract delete(url: string, options?: any): Observable<any>;

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
    const httpHeaders = new HttpHeaders({ 'Authorization': authStr });
    return this._http.get(apiKeyPath, { headers: httpHeaders }).pipe(map((resp: any) => {
      const respBody = resp;
      this.setApiKey(resp.token);
      return respBody;
    }), catchError(e => e.json()));
  }

  base64encode(str: string): string {
    return btoa(str);
  }

  httpRetry(maxRetry: number = 10, minDelayMs: number = 2000, maxDelayMs: number = 3000) {
    return (src: Observable<any>) => src.pipe(
      retryWhen(errors => {
        const randomInterval = this.generateRandomInterval(minDelayMs, maxDelayMs);
        return errors.pipe(
          flatMap(error => error.status === 429 ? of(error) : throwError(error)),
          delay(randomInterval),
          take(maxRetry)
        );
      })
    );
  }

}

@Injectable({
  providedIn: 'root'
})
export class HttpService extends AbstractHttpService {

  constructor(private http: HttpClient) {
    super(http);
  }

  get(url: string, options?: any, httpHeadersParam?: HttpHeaders): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = httpHeadersParam || new HttpHeaders({ 'Authorization': authToken });
    const params = new HttpParams({
      fromObject: options,
    });
    return this.http.get(url, { headers: httpHeaders, params })
      .pipe(
        this.httpRetry(),
        map((resp: any) => {
          return resp;
        }),
        catchError((e) => {
          return observableThrowError(e);
        })
      );
  }

  post(url: string, formData: any, options?: any): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = new HttpHeaders({ 'Authorization': authToken });
    return this.http.post(url, formData, { headers: httpHeaders }).pipe(map((resp: any) => {
      return resp;
    }), catchError((e) => {
      return observableThrowError(e);
    }));
  }

  put(url: string, formData: any, options?: any): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = new HttpHeaders({ 'Authorization': authToken });
    return this.http.put(url, formData, { headers: httpHeaders }).pipe(map((resp: any) => {
      return resp;
    }), catchError((e) => {
      return observableThrowError(e);
    }));
  }

  patch(url: string, formData: any, options?: any): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = new HttpHeaders({ 'Authorization': authToken });
    return this.http.patch(url, formData, { headers: httpHeaders }).pipe(map((resp: any) => {
      return resp;
    }), catchError((e) => {
      return observableThrowError(e);
    }));
  }

  options(url: string, options?: any): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = new HttpHeaders({ 'Authorization': authToken });
    return this.http.options(url, { headers: httpHeaders }).pipe(map((resp: any) => {
      return resp;
    }), catchError((e) => {
      return observableThrowError(e);
    }));
  }

  delete(url: string, options?: any): Observable<any> {
    const authToken = ` Token ${this.apiKey}`;
    const httpHeaders = new HttpHeaders({ 'Authorization': authToken });
    return this.http.delete(url, { headers: httpHeaders }).pipe(map((resp: any) => {
      return resp;
    }), catchError((e) => {
      return observableThrowError(e);
    }));
  }

}
