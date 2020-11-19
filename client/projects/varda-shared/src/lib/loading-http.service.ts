import { Injectable } from '@angular/core';
import { AbstractHttpService, HttpService } from './http.service';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { debounceTime, finalize } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class LoadingHttpService extends AbstractHttpService {
  private _loadingCount: number;
  private _isLoading: BehaviorSubject<boolean>;

  constructor(
    private http: HttpService,
    private client: HttpClient
  ) {
    super(client);
    this._loadingCount = 0;
    this._isLoading = new BehaviorSubject<boolean>(false);
  }

  isLoading(): Observable<boolean> {
    return this._isLoading.asObservable();
  }

  isLoadingWithDebounce(milliseconds = 500): Observable<boolean> {
    return this._isLoading.asObservable().pipe(debounceTime(milliseconds));
  }

  addLoader<T>(obs: Observable<T>): Observable<T> {
    this._loadingCount++;
    this._isLoading.next(true);

    return obs.pipe(finalize(() => {
      this._loadingCount--;
      if (this._loadingCount === 0) {
        this._isLoading.next(false);
      }
    }));
  }


  delete(url: string, options?: any): Observable<any> {
    return this.addLoader(this.http.delete(url, options));
  }

  get(url: string, options?: any, httpHeadersParam?: HttpHeaders): Observable<any> {
    return this.addLoader(this.http.get(url, options, httpHeadersParam));
  }

  getAllResults(url: string, backendUrl: string, options?: any): Observable<any> {
    return this.addLoader(this.http.getAllResults(url, backendUrl, options));
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
