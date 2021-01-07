import { Injectable } from '@angular/core';
import { LoadingHttpService, VardaUserDTO } from 'varda-shared';
import { environment } from '../../environments/environment';
import { Observable, BehaviorSubject } from 'rxjs';
import { HuoltajanLapsiDTO } from '../utilities/models/dto/huoltajan-lapsi-dto';
import { HuoltajaTranslations } from '../../assets/i18n/translations.enum';
import { VardaApiServiceInterface } from 'projects/varda-shared/src/lib/dto/vardaApiService.interface';

@Injectable({
  providedIn: 'root'
})
export class HuoltajaApiService implements VardaApiServiceInterface {
  huoltajaApi = `${environment.huoltajaBackendUrl}/api/oppija`;
  loginApi = `${environment.huoltajaBackendUrl}/api/user`;
  opintopolkuUrl = 'https://virkailija.testiopintopolku.fi';
  currentUser = new BehaviorSubject<HuoltajanLapsiDTO>(null);
  private vardaDomains = ['opintopolku.fi', 'studieinfo.fi', 'studyinfo.fi'];

  constructor(private http: LoadingHttpService) {
    if (this.vardaDomains.includes(window.location.hostname)) {
      this.opintopolkuUrl = 'https://virkailija.opintopolku.fi';
    }
  }

  setCurrentUser(lapsiDto: HuoltajanLapsiDTO): void {
    this.currentUser.next(lapsiDto);
    this.currentUser.complete();
  }

  getCurrentUser(): Observable<HuoltajanLapsiDTO> {
    return this.currentUser.asObservable();
  }

  getUserInfo(): Observable<VardaUserDTO> {
    return this.http.get(`${this.loginApi}/data/`);
  }

  getHuoltajanLapsi(lapsi_oid: string): Observable<HuoltajanLapsiDTO> {
    return this.http.get(`${this.huoltajaApi}/v1/huoltajanlapsi/${lapsi_oid}/`);
  }

  getVardaDomains(): Array<string> {
    return this.vardaDomains;
  }

  getTranslationCategory(): string {
    return environment.localizationCategory;
  }

  getLocalizationApi(): string {
    return `${environment.huoltajaBackendUrl}/api/julkinen/v1/localisation`;
  }

  getTranslationEnum(): any {
    return HuoltajaTranslations;
  }
}
