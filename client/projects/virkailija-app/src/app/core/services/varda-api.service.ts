import { Observable } from 'rxjs';
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { VardaUtilityService } from './varda-utility.service';
import { LoadingHttpService, VardaUserDTO } from 'varda-shared';
import { VardaHenkiloDTO } from '../../utilities/models';
import { VardaApiServiceInterface } from 'varda-shared/lib/models/vardaApiService.interface';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import {
  VardaSetPaattymisPvmDTO,
  VardaSetPaattymisPvmPostDTO, VardaSetPaattymisPvmPostResultDTO
} from '../../utilities/models/dto/varda-set-paattymis-pvm-dto.model';

@Injectable()
export class VardaApiService implements VardaApiServiceInterface {
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

  constructor(
    private vardaUtilityService: VardaUtilityService,
    private http: LoadingHttpService
  ) { }

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

  createHenkilo(createParam: any): Observable<any> {
    return this.http.post(this.henkilotApiPath, createParam);
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

  postSetPaattymisPvm(params: VardaSetPaattymisPvmPostDTO): Observable<VardaSetPaattymisPvmPostResultDTO> {
    return this.http.post(`${environment.vardaAppUrl}/api/admin/set-paattymis-pvm/`, params);
  }

  getSetPaattymisPvm(identifier: string): Observable<VardaSetPaattymisPvmDTO> {
    return this.http.get(`${environment.vardaAppUrl}/api/admin/set-paattymis-pvm/${identifier}/`);
  }
}
