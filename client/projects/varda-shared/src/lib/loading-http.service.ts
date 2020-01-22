import { Injectable } from '@angular/core';
import {AbstractHttpService, HttpService} from './http.service';
import {HttpClient, HttpHeaders} from '@angular/common/http';
import {Observable} from 'rxjs';
import {finalize} from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class LoadingHttpService extends AbstractHttpService {
  private _loading: number;

  constructor(private http: HttpService,
              private client: HttpClient) {
    super(client);
    this._loading = 0;
  }

  // This could also return observable that pushes on when _loading changes from 0 to something or from something to 0.
  isLoading(): boolean {
    return !!this._loading;
  }

  addLoader<T>(obs: Observable<T>): Observable<T> {
    this._loading++;
    return obs.pipe(finalize(() => this._loading--));
  }


  delete(url: string, options?: any): Observable<any> {
    return this.addLoader(this.http.delete(url, options));
  }

  get(url: string, options?: any, httpHeadersParam?: HttpHeaders): Observable<any> {
    return this.addLoader(this.http.get(url, options, httpHeadersParam));
  }

  options(url: string, options?: any): Observable<any> {
    return this.addLoader(this.http.options(url, options));
  }

  patch(url: string, formData: any, options?: any): Observable<any> {
    return this.addLoader(this.http.patch(url, formData, options));
  }

  post(url: string, formData: any, options?: any): Observable<any> {
    return this.addLoader(this.http.post(url, formData, options));
  }

  put(url: string, formData: any, options?: any): Observable<any> {
    return this.addLoader(this.http.put(url, formData, options));
  }

}
