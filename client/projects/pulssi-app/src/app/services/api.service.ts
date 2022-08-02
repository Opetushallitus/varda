import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpHeaders } from '@angular/common/http';
import { LoadingHttpService } from 'varda-shared';
import { environment } from '../../environments/environment';
import { VardaApiServiceInterface } from 'varda-shared/lib/models/vardaApiService.interface';
import { PulssiDto } from '../models/pulssi-dto';
import { PulssiTranslations } from '../../assets/i18n/translations.enum';

@Injectable({
  providedIn: 'root'
})
export class ApiService implements VardaApiServiceInterface {
  private apiPath = `${environment.backendUrl}/api/julkinen`;

  constructor(private http: LoadingHttpService) { }

  getPulssi(params: Record<string, unknown>): Observable<PulssiDto> {
    return this.http.get(`${this.apiPath}/v1/pulssi/`, params, new HttpHeaders());
  }

  getLocalizationApi(): string {
    return `${environment.backendUrl}/api/julkinen/v1/localisation`;
  }

  getTranslationCategory(): string {
    return environment.localizationCategory;
  }

  getTranslationEnum(): Record<string, string> {
    return PulssiTranslations;
  }
}
