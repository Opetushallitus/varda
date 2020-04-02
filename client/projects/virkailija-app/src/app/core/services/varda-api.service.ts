import {EMPTY, Observable} from 'rxjs';
import {expand, map, reduce} from 'rxjs/operators';
import {Injectable} from '@angular/core';
import {environment} from '../../../environments/environment';
import {VardaUtilityService} from './varda-utility.service';
import {VardaToimipaikkaYhteenvetoDTO} from '../../utilities/models/dto/varda-toimipaikka-yhteenveto-dto.model';
import {VardaFieldsetArrayContainer} from '../../utilities/models/varda-fieldset.model';
import {
  VardaCreateMaksutietoDTO,
  VardaMaksutietoDTO,
  VardaUpdateMaksutietoDTO
} from '../../utilities/models/dto/varda-maksutieto-dto.model';
import {VardaPageDto} from '../../utilities/models/dto/varda-page-dto';
import {VardaKoodistoDto} from '../../utilities/models/dto/varda-koodisto-dto.model';
import {
  HenkilohakuResultDTO,
  HenkilohakuSearchDTO,
  HenkilohakuType,
  LapsiByToimipaikkaDTO,
  ToimipaikanLapsi
} from '../../utilities/models/dto/varda-henkilohaku-dto.model';
import {sha256} from 'js-sha256';
import {LoadingHttpService} from 'varda-shared';
import {AllVakajarjestajaSearchDto} from '../../utilities/models/varda-vakajarjestaja.model';
import {
  PaosToimintaCreateDto,
  PaosToimintaDto,
  PaosToimintatietoDto, PaosToimipaikkaDto,
  PaosToimipaikkatietoDto, PaosVakajarjestajaDto
} from '../../utilities/models/dto/varda-paos-dto';
import {VardaToimipaikkaSearchDto} from '../../utilities/models/dto/varda-toimipaikka-dto.model';

@Injectable()
export class VardaApiService {

  constructor(private vardaUtilityService: VardaUtilityService,
              private http: LoadingHttpService) { }

  private toimipaikatApiPath = `${environment.vardaApiUrl}/toimipaikat/`;
  private vakaJarjestajatApiPath = `${environment.vardaApiUrl}/vakajarjestajat/`;
  private toimipaikanLapsetUiPath = `${environment.vardaAppUrl}/api/ui/toimipaikat/`;
  private vakaJarjestajatUiPath = `${environment.vardaAppUrl}/api/ui/vakajarjestajat/`;
  private allVakaJarjestajatUiPath = `${environment.vardaAppUrl}/api/ui/all-vakajarjestajat/`;
  private henkilotApiPath = `${environment.vardaApiUrl}/henkilot/`;
  private haeHenkiloApiPath = `${environment.vardaApiUrl}/hae-henkilo/`;
  private lapsetApiPath = `${environment.vardaApiUrl}/lapset/`;
  private maksutiedotApiPath = `${environment.vardaApiUrl}/maksutiedot/`;
  private paosToimintaApiPath = `${environment.vardaApiUrl}/paos-toiminnat/`;
  private paosOikeusApiPath = `${environment.vardaApiUrl}/paos-oikeudet/`;
  private varhaiskasvatussuhteetApiPath = `${environment.vardaApiUrl}/varhaiskasvatussuhteet/`;
  private varhaiskasvatuspaatoksetApiPath = `${environment.vardaApiUrl}/varhaiskasvatuspaatokset/`;
  private kielipainotuksetApiPath = `${environment.vardaApiUrl}/kielipainotukset/`;
  private toimintapainotuksetApiPath = `${environment.vardaApiUrl}/toiminnallisetpainotukset/`;
  private fieldDefinitionsPath = 'assets/field-definitions/';

  static getVakajarjestajaUrlFromId(id: string) {
    return `/api/v1/vakajarjestajat/${id}/`;
  }

  static getToimipaikkaUrlFromId(id: string) {
    return `/api/v1/toimipaikat/${id}/`;
  }

  static getLapsiUrlFromId(id: string) {
    return `/api/v1/lapset/${id}/`;
  }

  getUserData(): Observable<any> {
    return this.http.get(`${environment.vardaAppUrl}/api/user/data/`).pipe(map((resp: any) => {
      return resp;
    }));
  }

  isLoggedInToCas(): Observable<any> {
    const opintopolkuUrl = this.vardaUtilityService.getOpintopolkuUrl(window.location.hostname);
    return this.http.get(`${opintopolkuUrl}/kayttooikeus-service/cas/me`);
  }

  getLogoutCasUrl(): string {
    const opintopolkuUrl = this.vardaUtilityService.getOpintopolkuUrl(window.location.hostname);
    return `${opintopolkuUrl}/service-provider-app/saml/logout`;
  }

  getHenkilot(): Observable<any> {
    return this.http.get(this.henkilotApiPath).pipe(map((resp: any) => {
      return resp.results;
    }));
  }

  getHenkiloBySsnOrHenkiloOid(searchParam: any): Observable<any> {
    return this.http.post(`${this.haeHenkiloApiPath}`, searchParam).pipe(map((resp: any) => {
      return resp;
    }));
  }

  getVakaJarjestajaById(id: string): Observable<any> {
    return this.http.get(`${this.vakaJarjestajatApiPath}${id}/`).pipe(map((resp: any) => {
      return resp;
    }));
  }

  getAllVakajarjestajaForLoggedInUser(): Observable<any> {
    return this.http.get(`${this.vakaJarjestajatUiPath}`).pipe(
      map((resp: any) => {
        return resp;
      })
    );
  }

  getToimipaikkaById(id: string): Observable<any> {
    return this.http.get(`${this.toimipaikatApiPath}${id}/`).pipe(map((resp: any) => {
      return resp;
    }));
  }

  getToimipaikatForVakaJarjestaja(vakaJarjestajaId: string, searchParams?: any, nextLink?: string): Observable<any> {
    let url = `${environment.vardaApiUrl}/vakajarjestajat/${vakaJarjestajaId}/toimipaikat/`;

    if (searchParams) {
      url += '?';
      const searchParamKeys = Object.keys(searchParams);
      searchParamKeys.forEach((key) => {
        const searchParamValue = searchParams[key];
        url += key + '=' + searchParamValue + '&';
      });
    }

    if (nextLink) {
      url = this.getVardaPrefixedUrl(nextLink);
    }

    return this.http.get(url).pipe(map((resp: any) => {
      return resp;
    }));
  }

  getLapsetForToimipaikka(toimipaikkaId: string, searchParams?: any, nextLink?: string): Observable<VardaPageDto<LapsiByToimipaikkaDTO>> {
    let url = `${this.toimipaikanLapsetUiPath}${toimipaikkaId}/lapset/`;

    if (searchParams) {
      searchParams.search = this.hashHetu(searchParams.search);

      url += '?';
      const searchParamKeys = Object.keys(searchParams);
      searchParamKeys.forEach((key) => {
        const searchParamValue = searchParams[key];
        url += key + '=' + searchParamValue + '&';
      });
    }

    if (nextLink) {
      url = this.getVardaPrefixedUrl(nextLink);
    }

    return this.http.get(url).pipe(map((resp: any) => {
      return resp;
    }));
  }

  getLapsiKooste(id: number): Observable<ToimipaikanLapsi> {
    return this.http.get(`${environment.vardaApiUrl}/lapset/${id}/kooste/`).pipe(map((resp: any) => {
      return resp;
    }));
  }

  getAllToimipaikatForVakaJarjestaja(vakaJarjestajaId: string): Observable<any> {
    const url = `${this.vakaJarjestajatUiPath}${vakaJarjestajaId}/toimipaikat/`;
    return this.http.get(url).pipe(
      map((resp: any) => {
        return {results: resp};
      })
    );
  }

  getAllVarhaiskasvatussuhteetByToimipaikka(toimipaikkaId: string): Observable<any> {
    const url = `${environment.vardaApiUrl}/toimipaikat/${toimipaikkaId}/varhaiskasvatussuhteet/`;
    return this.http.get(url).pipe(map((resp: any) => {
      return {results: resp.results, count: resp.count, next: resp.next};
    }));
  }

  getVarhaiskasvatussuhteetByPageNo(page?: string): Observable<any> {
    const url = `${environment.vardaApiUrl}/varhaiskasvatussuhteet/?page=${page}`;
    return this.http.get(url).pipe(map((resp: any) => {
      return resp.results;
    }));
  }

  getToimipaikatForVakaJarjestajaByPageNo(vakaJarjestajaId: string, page?: string): Observable<any> {
    const url = `${environment.vardaApiUrl}/vakajarjestajat/${vakaJarjestajaId}/toimipaikat/?page=${page}`;
    return this.http.get(url).pipe(map((resp: any) => {
      return resp.results;
    }));
  }

  getVakajarjestajaForLoggedInUserByPageNo(page?: string): Observable<any> {
    const url = `${environment.vardaApiUrl}/vakajarjestajat/?page=${page}`;
    return this.http.get(url).pipe(map((resp: any) => {
      return resp.results;
    }));
  }

  getAllVarhaiskasvatussuhteetByToimipaikkaByPageNo(toimipaikkaId: string, page?: string): Observable<any> {
    const url = `${environment.vardaApiUrl}/toimipaikat/${toimipaikkaId}/varhaiskasvatussuhteet/?page=${page}`;
    return this.http.get(url).pipe(map((resp: any) => {
      return resp.results;
    }));
  }

  getAllMaksutiedotByLapsiByPageNo(lapsiId: string, page?: number): Observable<Array<VardaMaksutietoDTO>> {
    const url = `${this.lapsetApiPath}${lapsiId}/maksutiedot/?page=${page}`;
    return this.http.get(url).pipe(map((resp: VardaPageDto<VardaMaksutietoDTO>) => {
      return resp.results;
    }));
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

  getVarhaiskasvatussuhteetByLapsi(lapsiId: string): Observable<any> {
    const url = `${environment.vardaApiUrl}/lapset/${lapsiId}/varhaiskasvatussuhteet/`;
    return this.http.get(url).pipe(map((resp: any) => {
      return resp.results;
    }));
  }

  getVarhaiskasvatuspaatoksetByLapsi(lapsiId: string): Observable<any> {
    const url = `${environment.vardaApiUrl}/lapset/${lapsiId}/varhaiskasvatuspaatokset/`;
    return this.http.get(url).pipe(map((resp: any) => {
      return resp.results;
    }));
  }

  getYhteenveto(toimipaikkaId: string): Observable<VardaToimipaikkaYhteenvetoDTO> {
    const url = `${environment.vardaApiUrl}/vakajarjestajat/${toimipaikkaId}/yhteenveto/`;
    return this.http.get(url).pipe(map((resp: VardaToimipaikkaYhteenvetoDTO) => resp));
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

  getVarhaiskasvatussuhdeFields(): Observable<any> {
    return this.http.get(`${this.fieldDefinitionsPath}varhaiskasvatussuhteet.json`);
  }

  getMaksutietoFields(): Observable<VardaFieldsetArrayContainer> {
    return this.http.get(`${this.fieldDefinitionsPath}maksutiedot.json`);
  }

  getHuoltajaFields(): Observable<VardaFieldsetArrayContainer> {
    return this.http.get(`${this.fieldDefinitionsPath}huoltaja.json`);
  }

  getVarhaiskasvatuspaatosFields(): Observable<any> {
    return this.http.get(`${this.fieldDefinitionsPath}varhaiskasvatuspaatokset.json`);
  }

  getLapsiMaksupaatokset(lapsi_id: number): Observable<VardaPageDto<VardaMaksutietoDTO>> {
    const url = `${this.lapsetApiPath}${lapsi_id}/maksutiedot/`;
    return this.http.get(url);
  }

  createToimipaikka(data: any): Observable<any> {
    return this.http.post(this.toimipaikatApiPath, data);
  }

  createLapsi(data: any): Observable<any> {
    return this.http.post(this.lapsetApiPath, data);
  }

  createHenkilo(createParam: any): Observable<any> {
    return this.http.post(this.henkilotApiPath, createParam);
  }

  createVarhaiskasvatussuhde(data: any): Observable<any> {
    return this.http.post(this.varhaiskasvatussuhteetApiPath, data);
  }

  createVarhaiskasvatuspaatos(data: any): Observable<any> {
    return this.http.post(this.varhaiskasvatuspaatoksetApiPath, data);
  }

  createKielipainotus(data: any): Observable<any> {
    return this.http.post(this.kielipainotuksetApiPath, data);
  }

  createToimintapainotus(data: any): Observable<any> {
    return this.http.post(this.toimintapainotuksetApiPath, data);
  }

  editToimipaikka(toimipaikkaId: string, data: any): Observable<any> {
    return this.http.put(`${environment.vardaApiUrl}/toimipaikat/${toimipaikkaId}/`, data);
  }

  editVarhaiskasvatussuhde(varhaiskasvatussuhdeId: string, data: any): Observable<any> {
    return this.http.put(`${environment.vardaApiUrl}/varhaiskasvatussuhteet/${varhaiskasvatussuhdeId}/`, data);
  }

  editVarhaiskasvatuspaatos(varhaiskasvatuspaatosId: string, data: any): Observable<any> {
    return this.http.put(`${environment.vardaApiUrl}/varhaiskasvatuspaatokset/${varhaiskasvatuspaatosId}/`, data);
  }

  editKielipainotus(kielipainotusId: string, data: any): Observable<any> {
    return this.http.put(`${environment.vardaApiUrl}/kielipainotukset/${kielipainotusId}/`, data);
  }

  editToimintapainotus(toimintapainotusId: string, data: any): Observable<any> {
    return this.http.put(`${environment.vardaApiUrl}/toiminnallisetpainotukset/${toimintapainotusId}/`, data);
  }

  patchVakajarjestaja(vakaJarjestajaId: string, data: any): Observable<any> {
    return this.http.patch(`${environment.vardaApiUrl}/vakajarjestajat/${vakaJarjestajaId}/`, data);
  }

  deleteKielipainotus(kielipainotusId: string): Observable<any> {
    return this.http.delete(`${environment.vardaApiUrl}/kielipainotukset/${kielipainotusId}/`);
  }

  deleteToimintapainotus(toimintapainotusId: string): Observable<any> {
    return this.http.delete(`${environment.vardaApiUrl}/toiminnallisetpainotukset/${toimintapainotusId}/`);
  }

  deleteVarhaiskasvatuspaatos(varhaiskasvatuspaatosId: string): Observable<any> {
    return this.http.delete(`${environment.vardaApiUrl}/varhaiskasvatuspaatokset/${varhaiskasvatuspaatosId}/`);
  }

  deleteVarhaiskasvatussuhde(varhaiskasvatussuhdeId: string): Observable<any> {
    return this.http.delete(`${environment.vardaApiUrl}/varhaiskasvatussuhteet/${varhaiskasvatussuhdeId}/`);
  }

  deleteLapsi(lapsiId: string): Observable<any> {
    return this.http.delete(`${environment.vardaApiUrl}/lapset/${lapsiId}/`);
  }

  getKielikoodistoOptions(): Observable<any> {
    const opintopolkuUrl = this.getOpintopolkuUrlFromHost();
    return this.http.getWithCallerId(`${opintopolkuUrl}/koodisto-service/rest/json/kielikoodistoopetushallinto/koodi`);
  }

  getKuntakoodistoOptions(): Observable<any> {
    const opintopolkuUrl = this.getOpintopolkuUrlFromHost();
    return this.http.getWithCallerId(`${opintopolkuUrl}/koodisto-service/rest/json/kunta/koodi`);
  }

  getMaksunPerustekoodisto(): Observable<Array<VardaKoodistoDto>> {
    const opintopolkuUrl = this.getOpintopolkuUrlFromHost();
    return this.http.getWithCallerId(`${opintopolkuUrl}/koodisto-service/rest/json/vardamaksunperuste/koodi`);
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

  createMaksutieto(newMaksutietoDTO: VardaCreateMaksutietoDTO): Observable<VardaMaksutietoDTO> {
    return this.http.post(this.maksutiedotApiPath, newMaksutietoDTO);
  }

  updateMaksutieto(maksutietoId: number, updateMaksutietoDTO: VardaUpdateMaksutietoDTO): Observable<VardaMaksutietoDTO> {
    const url = `${this.maksutiedotApiPath}${maksutietoId}/`;
    return this.http.patch(url, updateMaksutietoDTO);
  }

  deleteMaksutieto(maksutietoId: number): Observable<any> {
    const url = `${this.maksutiedotApiPath}${maksutietoId}/`;
    return this.http.delete(url);
  }

  getHenkilohaku(vakajarjestajaId: number,
                 searchDto: HenkilohakuSearchDTO,
                 nextUrl?: string): Observable<VardaPageDto<HenkilohakuResultDTO>> {
    const mutableSearchDto = {...searchDto};
    mutableSearchDto.search = this.hashHetu(mutableSearchDto.search);
    const url = nextUrl && this.getVardaPrefixedUrl(nextUrl)
      || `${this.vakaJarjestajatApiPath}${vakajarjestajaId}/henkilohaku/${searchDto.type || HenkilohakuType.lapset}/`;
    // If getting next page query it as is
    const params = nextUrl ? null : mutableSearchDto;
    return this.http.get(url, params);
  }

  getAllPaosToimijat(searchDto: AllVakajarjestajaSearchDto, page: number = 1): Observable<VardaPageDto<PaosVakajarjestajaDto>> {
    const url = this.allVakaJarjestajatUiPath;
    return this.http.get(url, {...searchDto, ...{page}});
  }

  getAllPaosToimipaikat(id: string, searchDto: VardaToimipaikkaSearchDto, page: number = 1): Observable<VardaPageDto<PaosToimipaikkaDto>> {
    const url = `${this.vakaJarjestajatUiPath}${id}/all-toimipaikat/`;
    return this.http.get(url, {...searchDto, ...{page}});
  }

  createPaosToiminta(createDto: PaosToimintaCreateDto): Observable<PaosToimintaDto> {
    const url = this.paosToimintaApiPath;
    return this.http.post(url, createDto);
  }

  getPaosToimijat(id: string, page: number): Observable<VardaPageDto<PaosToimintatietoDto>> {
    const url = `${this.vakaJarjestajatApiPath}${id}/paos-toimijat/`;
    return this.http.get(url, {page});
  }

  getPaosToimipaikat(id: string, page: number = 1): Observable<VardaPageDto<PaosToimipaikkatietoDto>> {
    const url = `${this.vakaJarjestajatApiPath}${id}/paos-toimipaikat/`;
    return this.http.get(url, {page});
  }

  // Generic function to fetch all pages sequentially.
  getAllPagesSequentially<T>(method: (page: number) => Observable<VardaPageDto<T>>): Observable<Array<T>> {
    return new Observable(subscriber => {
      method(1).pipe(
        // Index start from 0
        expand((result, index) => {
          return result.next ? method(index + 2) : EMPTY;
        }),
        reduce((acc, result) => acc.concat(result.results), []),
        // catchError(err => of(err)),
      ).subscribe({
        next: res => {
          subscriber.next(res);
          subscriber.complete();
        },
        error: err => subscriber.error(err),
      });
    });
  }

  deletePaosToiminta(paostoimintaId: string) {
    const url = `${this.paosToimintaApiPath}${paostoimintaId}/`;
    return this.http.delete(url);
  }

  updatePaosOikeus(paosOikeusId: number, savingToimijaId: string) {
    const url = `${this.paosOikeusApiPath}${paosOikeusId}/`;
    const savingToimijaUrl = VardaApiService.getVakajarjestajaUrlFromId(`${savingToimijaId}`);
    return this.http.put(url, {tallentaja_organisaatio: savingToimijaUrl});
  }

  hashHetu(rawHetu: string) {
    const hetu_regex = /^\d{6}[A+\-]\d{3}[0-9A-FHJ-NPR-Y]$/;
    if (rawHetu && hetu_regex.test(rawHetu)) {
      return sha256.create().update(rawHetu).hex();
    }
    return rawHetu;
  }
}
