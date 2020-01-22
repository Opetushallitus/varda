import { Injectable } from '@angular/core';
import {HttpService, VardaUserDTO} from 'varda-shared';
import {environment} from '../../environments/environment';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class HuoltajaApiService {
  huoltajaApi = `${environment.huoltajaAppUrl}/huoltaja-api`;
  loginApi = `${environment.huoltajaAppUrl}/api/user`;

  constructor(private client: HttpService) { }

  getUserInfo(): Observable<VardaUserDTO> {
    const url = `${this.loginApi}/data/`;
    return this.client.get(url);
  }
}
