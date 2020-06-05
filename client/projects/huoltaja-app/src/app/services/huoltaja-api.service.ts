import { Injectable } from '@angular/core';
import { LoadingHttpService, VardaUserDTO } from 'varda-shared';
import { environment } from '../../environments/environment';
import { Observable, BehaviorSubject } from 'rxjs';
import { TranslationDTO } from '../utilities/models/dto/translation-dto';
import { HuoltajanLapsiDTO } from '../utilities/models/dto/huoltajan-lapsi-dto';

@Injectable({
  providedIn: 'root'
})
export class HuoltajaApiService {
  // TODO: siirrä .env kunhan koodisto- ja lokalisaatiopalvelu haetaan sisäisesti esim. https://jira.eduuni.fi/browse/CSCVARDA-1258
  huoltajaApi = `${environment.huoltajaAppUrl}/api/oppija`;
  loginApi = `${environment.huoltajaAppUrl}/api/user`;
  opintopolkuUrl = 'https://virkailija.testiopintopolku.fi';
  currentUser = new BehaviorSubject<HuoltajanLapsiDTO>(null);

  constructor(private http: LoadingHttpService) {
    if (window.location.hostname === 'opintopolku.fi') {
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

  getKielikoodistoOptions(): Observable<any> {
    return this.http.getWithCallerId(`${this.opintopolkuUrl}/koodisto-service/rest/json/kielikoodistoopetushallinto/koodi`);
  }

  getKuntakoodistoOptions(): Observable<any> {
    return this.http.getWithCallerId(`${this.opintopolkuUrl}/koodisto-service/rest/json/kunta/koodi`);
  }

  getTranslations(): Observable<TranslationDTO> {
    return this.http.getWithCallerId(`${this.opintopolkuUrl}/lokalisointi/cxf/rest/v1/localisation?category=varda-huoltaja`);
  }
}
