import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { VardaUtilityService } from './varda-utility.service';
import { LoadingHttpService, VardaUserDTO } from 'varda-shared';
import { VardaHenkiloDTO } from '../../utilities/models';
import { VardaApiServiceInterface } from 'varda-shared/lib/dto/vardaApiService.interface';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

@Injectable()
export class VardaApiService implements VardaApiServiceInterface {

  constructor(
    private vardaUtilityService: VardaUtilityService,
    private http: LoadingHttpService
  ) { }

  private toimipaikatApiPath = `${environment.vardaApiUrl}/toimipaikat/`;
  private henkilotApiPath = `${environment.vardaApiUrl}/henkilot/`;
  private kielipainotuksetApiPath = `${environment.vardaApiUrl}/kielipainotukset/`;
  private toimintapainotuksetApiPath = `${environment.vardaApiUrl}/toiminnallisetpainotukset/`;
  private fieldDefinitionsPath = 'assets/field-definitions/';

  private vakaJarjestajatApiPath = `${environment.vardaApiUrl}/vakajarjestajat/`;
  private vakaJarjestajatUiPath = `${environment.vardaAppUrl}/api/ui/vakajarjestajat/`;
  private allVakaJarjestajatUiPath = `${environment.vardaAppUrl}/api/ui/all-vakajarjestajat/`;
  private haeHenkiloApiPath = `${environment.vardaApiUrl}/hae-henkilo/`;
  private lapsetApiPath = `${environment.vardaApiUrl}/lapset/`;
  private maksutiedotApiPath = `${environment.vardaApiUrl}/maksutiedot/`;
  private paosToimintaApiPath = `${environment.vardaApiUrl}/paos-toiminnat/`;
  private paosOikeusApiPath = `${environment.vardaApiUrl}/paos-oikeudet/`;
  private varhaiskasvatussuhteetApiPath = `${environment.vardaApiUrl}/varhaiskasvatussuhteet/`;
  private varhaiskasvatuspaatoksetApiPath = `${environment.vardaApiUrl}/varhaiskasvatuspaatokset/`;
  private henkilostoApiPath = `${environment.vardaAppUrl}/api/henkilosto/v1/`;

  static getVakajarjestajaUrlFromId(id: number) {
    return `/api/v1/vakajarjestajat/${id}/`;
  }

  static getToimipaikkaUrlFromId(id: number) {
    return `/api/v1/toimipaikat/${id}/`;
  }

  static getLapsiUrlFromId(id: number) {
    return `/api/v1/lapset/${id}/`;
  }

  getTranslationCategory() {
    return environment.localizationCategory;
  }

  getLocalizationApi() {
    return `${environment.vardaAppUrl}/api/julkinen/v1/localisation`;
  }

  getTranslationEnum() {
    return VirkailijaTranslations;
  }


  getUserData(): Observable<VardaUserDTO> {
    return this.http.get(`${environment.vardaAppUrl}/api/user/data/`);
  }

  isLoggedInToCas(): Observable<any> {
    const opintopolkuUrl = this.vardaUtilityService.getOpintopolkuUrl(window.location.hostname);
    return this.http.get(`${opintopolkuUrl}/kayttooikeus-service/cas/me`);
  }

  getLogoutCasUrl(): string {
    const opintopolkuUrl = this.vardaUtilityService.getOpintopolkuUrl(window.location.hostname);
    return `${opintopolkuUrl}/service-provider-app/saml/logout`;
  }

  getHenkilo(henkiloId: number): Observable<VardaHenkiloDTO> {
    return this.http.get(`${this.henkilotApiPath}${henkiloId}/`);
  }

  getKielipainotuksetByToimipaikka(toimipaikkaId: string): Observable<any> {
    const url = `${environment.vardaApiUrl}/toimipaikat/${toimipaikkaId}/kielipainotukset/`;
    return this.http.get(url).pipe(map((resp: any) => {
      return resp.results;
    }));
  }

  getToimintapainotuksetByToimipaikka(toimipaikkaId: string): Observable<any> {
    const url = `${environment.vardaApiUrl}/toimipaikat/${toimipaikkaId}/toiminnallisetpainotukset/`;
    return this.http.get(url).pipe(map((resp: any) => {
      return resp.results;
    }));
  }


  getToimipaikkaFields(): Observable<any> {
    return this.http.get(`${this.fieldDefinitionsPath}toimipaikat.json`);
  }

  getToimintapainotusFields(): Observable<any> {
    return this.http.get(`${this.fieldDefinitionsPath}toimintapainotukset.json`);
  }

  getKielipainotusFields(): Observable<any> {
    return this.http.get(`${this.fieldDefinitionsPath}kielipainotukset.json`);
  }

  createHenkilo(createParam: any): Observable<any> {
    return this.http.post(this.henkilotApiPath, createParam);
  }

  createToimipaikka(data: any): Observable<any> {
    return this.http.post(this.toimipaikatApiPath, data);
  }

  editToimipaikka(toimipaikkaId: string, data: any): Observable<any> {
    return this.http.put(`${environment.vardaApiUrl}/toimipaikat/${toimipaikkaId}/`, data);
  }

  createToimintapainotus(data: any): Observable<any> {
    return this.http.post(this.toimintapainotuksetApiPath, data);
  }

  editToimintapainotus(toimintapainotusId: string, data: any): Observable<any> {
    return this.http.put(`${environment.vardaApiUrl}/toiminnallisetpainotukset/${toimintapainotusId}/`, data);
  }

  createKielipainotus(data: any): Observable<any> {
    return this.http.post(this.kielipainotuksetApiPath, data);
  }

  editKielipainotus(kielipainotusId: string, data: any): Observable<any> {
    return this.http.put(`${environment.vardaApiUrl}/kielipainotukset/${kielipainotusId}/`, data);
  }

  deleteKielipainotus(kielipainotusId: string): Observable<any> {
    return this.http.delete(`${environment.vardaApiUrl}/kielipainotukset/${kielipainotusId}/`);
  }

  deleteToimintapainotus(toimintapainotusId: string): Observable<any> {
    return this.http.delete(`${environment.vardaApiUrl}/toiminnallisetpainotukset/${toimintapainotusId}/`);
  }

  getOpintopolkuUrlFromHost(): string {
    let opintopolkuUrl = this.vardaUtilityService.getOpintopolkuUrl(window.location.hostname);
    if (!opintopolkuUrl) {
      opintopolkuUrl = 'https://virkailija.testiopintopolku.fi';
    }
    return opintopolkuUrl;
  }

  getVardaPrefixedUrl(endpoint: string): string {
    let url = endpoint;
    if (environment.production) {
      url = `/varda${endpoint}`;
    }
    return url;
  }

}
