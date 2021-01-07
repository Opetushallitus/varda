import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpHeaders } from '@angular/common/http';
import { LoadingHttpService } from 'varda-shared';
import { environment } from '../../environments/environment';
import { KoodistoDto } from '../models/koodisto-dto';

@Injectable({
  providedIn: 'root'
})
export class PublicApiService {
  private julkinenApiPath = `${environment.publicAppUrl}/api/julkinen`;

  constructor(private http: LoadingHttpService) { }

  getKoodistot(params: Object): Observable<Array<KoodistoDto>> {
    const url = this.setParams(`${this.julkinenApiPath}/v1/koodistot/`, params);
    // Overwrite headers so that Authorization isn't required
    return this.http.get(url, null, new HttpHeaders());
  }

  private setParams(url, params) {
    if (params) {
      url += '?';
      const searchParamKeys = Object.keys(params);
      searchParamKeys.forEach((key) => {
        const searchParamValue = params[key];
        url += key + '=' + searchParamValue + '&';
      });
      return url.slice(0, -1);
    }
  }
}
