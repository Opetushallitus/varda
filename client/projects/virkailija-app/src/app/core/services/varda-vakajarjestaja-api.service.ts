import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, Subject, tap } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { LoadingHttpService } from 'varda-shared';
import { environment } from '../../../environments/environment';
import { VardaVakajarjestaja, VardaVakajarjestajaUi } from '../../utilities/models';
import {
  KielipainotusDTO,
  ToiminnallinenPainotusDTO,
  ToimipaikkaKooste,
  VardaToimipaikkaDTO,
  VardaToimipaikkaMinimalDto
} from '../../utilities/models/dto/varda-toimipaikka-dto.model';
import { PuutteellinenErrorDTO } from '../../utilities/models/dto/varda-puutteellinen-dto.model';
import { VardaRaportitService } from './varda-raportit.service';
import { AuthService } from '../auth/auth.service';


@Injectable()
export class VardaVakajarjestajaApiService {
  activeToimipaikka = new BehaviorSubject<ToimipaikkaKooste>(null);

  private toimipaikatApiPath = `${environment.vardaApiUrl}/toimipaikat`;
  private vakaJarjestajatApiPath = `${environment.vardaApiUrl}/vakajarjestajat`;
  private vardaUiPath = `${environment.vardaAppUrl}/api/ui`;

  private updateToimipaikkaList$ = new Subject();
  private toimipaikkaFormErrorList = new BehaviorSubject<Array<PuutteellinenErrorDTO>>([]);

  constructor(
    private http: LoadingHttpService,
    private raportitService: VardaRaportitService,
    private authService: AuthService
  ) { }

  getToimipaikkaUrl(id) {
    return `/api/v1/toimipaikat/${id}/`;
  }

  getVakajarjestajat(): Observable<Array<VardaVakajarjestajaUi>> {
    return this.http.get(`${this.vardaUiPath}/vakajarjestajat/`);
  }

  getVakajarjestaja(vakajarjestajaId: number) {
    return this.http.get(`${this.vakaJarjestajatApiPath}/${vakajarjestajaId}/`);
  }

  patchVakajarjestaja(vakajarjestajaId: number, vakajarjestajaData: VardaVakajarjestaja): Observable<VardaVakajarjestajaUi> {
    return this.http.patch(`${this.vakaJarjestajatApiPath}/${vakajarjestajaId}/`, vakajarjestajaData);
  }

  /** catchError returns empty array, because not all user roles have access to /toimipaikat */
  getToimipaikat(vakajarjestajaId: number, searchFilters?: Record<string, any>): Observable<Array<VardaToimipaikkaMinimalDto>> {
    return this.http.getAllResults(
      `${this.vardaUiPath}/vakajarjestajat/${vakajarjestajaId}/toimipaikat/`,
      environment.vardaAppUrl,
      { page_size: 500, ...searchFilters }
    ).pipe(
      catchError((err: Error) => of([])),
      tap(toimipaikat => {
        this.authService.initUserPermissions(toimipaikat);
      })
    );
  }

  createToimipaikka(toimipaikkaDTO: VardaToimipaikkaDTO): Observable<VardaToimipaikkaDTO> {
    return this.http.post(`${this.toimipaikatApiPath}/`, toimipaikkaDTO);
  }

  updateToimipaikka(toimipaikkaDTO: VardaToimipaikkaDTO): Observable<VardaToimipaikkaDTO> {
    return this.http.put(`${this.toimipaikatApiPath}/${toimipaikkaDTO.id}/`, toimipaikkaDTO);
  }

  createKielipainotus(kielipainotusDTO: KielipainotusDTO): Observable<KielipainotusDTO> {
    return this.http.post(`${environment.vardaApiUrl}/kielipainotukset/`, kielipainotusDTO);
  }

  updateKielipainotus(kielipainotusDTO: KielipainotusDTO): Observable<KielipainotusDTO> {
    return this.http.put(`${environment.vardaApiUrl}/kielipainotukset/${kielipainotusDTO.id}/`, kielipainotusDTO);
  }

  deleteKielipainotus(kielipainotusId: number): Observable<void> {
    return this.http.delete(`${environment.vardaApiUrl}/kielipainotukset/${kielipainotusId}/`);
  }

  createToimintapainotus(toimintapainotusDTO: ToiminnallinenPainotusDTO): Observable<ToiminnallinenPainotusDTO> {
    return this.http.post(`${environment.vardaApiUrl}/toiminnallisetpainotukset/`, toimintapainotusDTO);
  }

  updateToimintapainotus(toimintapainotusDTO: ToiminnallinenPainotusDTO): Observable<ToiminnallinenPainotusDTO> {
    return this.http.put(`${environment.vardaApiUrl}/toiminnallisetpainotukset/${toimintapainotusDTO.id}/`, toimintapainotusDTO);
  }

  deleteToimintapainotus(toimintapainotusId: number): Observable<void> {
    return this.http.delete(`${environment.vardaApiUrl}/toiminnallisetpainotukset/${toimintapainotusId}/`);
  }

  listenToimipaikkaListUpdate(): Observable<any> {
    return this.updateToimipaikkaList$.asObservable();
  }

  sendToimipaikkaListUpdate() {
    this.updateToimipaikkaList$.next(true);
  }

  initFormErrorList(vakajarjestajaID: number, toimipaikka: VardaToimipaikkaMinimalDto | VardaToimipaikkaDTO) {
    this.toimipaikkaFormErrorList.next([]);
    if (toimipaikka.id) {
      const searchFilter = {
        page: 1,
        page_size: 100,
        search: toimipaikka.id.toString()
      };

      this.raportitService.getToimipaikkaErrorList(vakajarjestajaID, searchFilter).subscribe(data => {
        const toimipaikkaResult = data.results.find(result => result.toimipaikka_id === toimipaikka.id);
        if (toimipaikkaResult?.errors) {
          this.toimipaikkaFormErrorList.next(toimipaikkaResult.errors);
        }
      });
    }
  }

  getFormErrorList(): Observable<Array<PuutteellinenErrorDTO>> {
    return this.toimipaikkaFormErrorList.asObservable();
  }
}
