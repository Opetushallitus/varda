import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { LoadingHttpService } from 'varda-shared';
import { environment } from '../../../environments/environment';
import { VardaVakajarjestaja, VardaVakajarjestajaUi } from '../../utilities/models';
import { VardaPageDto } from '../../utilities/models/dto/varda-page-dto';
import { KielipainotusDTO, ToiminnallinenPainotusDTO, VardaToimipaikkaDTO, VardaToimipaikkaMinimalDto } from '../../utilities/models/dto/varda-toimipaikka-dto.model';


@Injectable()
export class VardaVakajarjestajaApiService {

  private toimipaikatApiPath = `${environment.vardaApiUrl}/toimipaikat`;
  private vakaJarjestajatApiPath = `${environment.vardaApiUrl}/vakajarjestajat`;
  private vardaUiPath = `${environment.vardaAppUrl}/api/ui`;

  constructor(private http: LoadingHttpService) { }

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
  getToimipaikat(vakajarjestajaId: number): Observable<Array<VardaToimipaikkaMinimalDto>> {
    return this.http.getAllResults(
      `${this.vardaUiPath}/vakajarjestajat/${vakajarjestajaId}/toimipaikat/`,
      environment.vardaAppUrl,
      { page_size: 500 }
    ).pipe(catchError((err: Error) => of([])));
  }

  getToimipaikka(toimipaikkaId: number): Observable<VardaToimipaikkaDTO> {
    return this.http.get(`${this.toimipaikatApiPath}/${toimipaikkaId}/`);
  }

  createToimipaikka(toimipaikkaDTO: VardaToimipaikkaDTO): Observable<VardaToimipaikkaDTO> {
    return this.http.post(`${this.toimipaikatApiPath}/`, toimipaikkaDTO);
  }

  updateToimipaikka(toimipaikkaDTO: VardaToimipaikkaDTO): Observable<VardaToimipaikkaDTO> {
    return this.http.put(`${this.toimipaikatApiPath}/${toimipaikkaDTO.id}/`, toimipaikkaDTO);
  }

  patchToimipaikka(toimipaikkaDTO: VardaToimipaikkaDTO): Observable<VardaToimipaikkaDTO> {
    return this.http.patch(`${this.toimipaikatApiPath}/${toimipaikkaDTO.id}/`, toimipaikkaDTO);
  }

  deleteToimipaikka(toimipaikkaId: number): Observable<void> {
    return this.http.delete(`${this.toimipaikatApiPath}/${toimipaikkaId}/`);
  }

  getKielipainotukset(toimipaikkaId: number): Observable<VardaPageDto<KielipainotusDTO>> {
    return this.http.get(`${environment.vardaApiUrl}/toimipaikat/${toimipaikkaId}/kielipainotukset/`);
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

  getToimintapainotukset(toimipaikkaId: number): Observable<VardaPageDto<ToiminnallinenPainotusDTO>> {
    return this.http.get(`${environment.vardaApiUrl}/toimipaikat/${toimipaikkaId}/toiminnallisetpainotukset/`);
  }

  createToimintapainotus(toimintapainotusDTO: KielipainotusDTO): Observable<ToiminnallinenPainotusDTO> {
    return this.http.post(`${environment.vardaApiUrl}/toiminnallisetpainotukset/`, toimintapainotusDTO);
  }

  updateToimintapainotus(toimintapainotusDTO: KielipainotusDTO): Observable<ToiminnallinenPainotusDTO> {
    return this.http.put(`${environment.vardaApiUrl}/toiminnallisetpainotukset/${toimintapainotusDTO.id}/`, toimintapainotusDTO);
  }

  deleteToimintapainotus(toimintapainotusId: number): Observable<void> {
    return this.http.delete(`${environment.vardaApiUrl}/toiminnallisetpainotukset/${toimintapainotusId}/`);
  }

}
