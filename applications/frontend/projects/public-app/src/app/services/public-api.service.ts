import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpHeaders } from '@angular/common/http';
import { LoadingHttpService } from 'varda-shared';
import { environment } from '../../environments/environment';
import { KoodistoDto } from '../models/koodisto-dto';
import { VardaApiServiceInterface } from 'varda-shared/lib/models/vardaApiService.interface';
import { PublicTranslations } from '../../assets/i18n/translations.enum';

@Injectable({
  providedIn: 'root'
})
export class PublicApiService implements VardaApiServiceInterface {
  private julkinenApiPath = `${environment.backendUrl}/api/julkinen`;

  constructor(private http: LoadingHttpService) { }

  getKoodistot(params: Record<string, unknown>): Observable<Array<KoodistoDto>> {
    const url = this.setParams(`${this.julkinenApiPath}/v1/koodistot/`, params);
    // Overwrite headers so that Authorization isn't required
    return this.http.get(url, null, new HttpHeaders());
  }

  getLocalizationApi(): string {
    return `${environment.backendUrl}/api/julkinen/v1/localisation`;
  }

  getTranslationCategory(): string {
    return environment.localizationCategory;
  }

  getTranslationEnum(): Record<string, string> {
    return PublicTranslations;
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
