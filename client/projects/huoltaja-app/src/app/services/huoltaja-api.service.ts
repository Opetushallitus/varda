import { Injectable } from '@angular/core';
import { LoadingHttpService, VardaUserDTO } from 'varda-shared';
import { environment } from '../../environments/environment';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class HuoltajaApiService {
  huoltajaApi = `${environment.huoltajaAppUrl}/oppija-api`;
  loginApi = `${environment.huoltajaAppUrl}/api/user`;

  constructor(private http: LoadingHttpService) { }

  getUserInfo(): Observable<VardaUserDTO> {
    return this.http.get(`${this.loginApi}/data/`);
  }

  getHuoltajanLapsi(lapsi_oid: string): Observable<any> {
    return this.http.get('/varda/assets/testilapsi.json');
    return this.http.get(`${this.huoltajaApi}/v1/huoltajanlapsi/${lapsi_oid}/`);
  }
}
