import { Injectable } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { environment } from 'projects/virkailija-app/src/environments/environment';
import { HenkiloListDTO } from '../../utilities/models/dto/varda-henkilo-dto.model';
import { VardaPageDto } from '../../utilities/models/dto/varda-page-dto';
import { HenkiloSearchFilter } from '../../varda-main/components/varda-main-frame/henkilo-section.abstract';
import { VardaRaportitService } from './varda-raportit.service';
import {
  LapsiListDTO, VardaLapsiDTO,
  VardaMaksutietoDTO,
  VardaMaksutietoSaveDTO, VardaVarhaiskasvatuspaatosDTO, VardaVarhaiskasvatussuhdeDTO
} from '../../utilities/models/dto/varda-lapsi-dto.model';
import { PuutteellinenErrorDTO } from '../../utilities/models/dto/varda-puutteellinen-dto.model';
import { LapsiKooste } from '../../utilities/models/dto/varda-henkilohaku-dto.model';
import {
  TukipaatosSearchFilter
} from "../../varda-main/components/varda-tukipaatos/varda-tukipaatos/varda-tukipaatos.component";
import {
  VardaTukipaatosDTO,
  VardaTukipaatosListsDTO,
} from "../../utilities/models/dto/varda-tukipaatos-dto.model";


@Injectable()
export class VardaLapsiService {
  activeLapsi = new BehaviorSubject<LapsiKooste>(null);

  private apiPath = `${environment.vardaAppUrl}/api/v1`;
  private updateLapsiList$ = new Subject();
  private lapsiFormErrorList = new BehaviorSubject<Array<PuutteellinenErrorDTO>>(null);

  constructor(
    private http: LoadingHttpService,
    private raportitService: VardaRaportitService
  ) { }

  getLapsiUrl(id: number) {
    return `/api/v1/lapset/${id}/`;
  }

  getVarhaiskasvatuspaatosUrl(id: number) {
    return `/api/v1/varhaiskasvatuspaatokset/${id}/`;
  }

  // listeners
  listenLapsiListUpdate(): Observable<any> {
    return this.updateLapsiList$.asObservable();
  }

  sendLapsiListUpdate() {
    this.updateLapsiList$.next(true);
  }

  getVakajarjestajaLapset(vakajarjestajaId: number, searchFilter: HenkiloSearchFilter): Observable<VardaPageDto<HenkiloListDTO>> {
    return this.http.get(`${environment.vardaAppUrl}/api/ui/vakajarjestajat/${vakajarjestajaId}/lapsi-list/`, searchFilter);
  }

  getLapsi(lapsiId: number): Observable<VardaLapsiDTO> {
    return this.http.get(`${this.apiPath}/lapset/${lapsiId}/`);
  }

  createLapsi(lapsiDTO: VardaLapsiDTO): Observable<VardaLapsiDTO> {
    return this.http.post(`${this.apiPath}/lapset/`, lapsiDTO);
  }

  deleteLapsi(lapsiId: number): Observable<void> {
    return this.http.delete(`${this.apiPath}/lapset/${lapsiId}/`);
  }

  // varhaiskasvatuspaatokset
  getVarhaiskasvatuspaatokset(lapsiId: number): Observable<Array<VardaVarhaiskasvatuspaatosDTO>> {
    return this.http.getAllResults(`${this.apiPath}/varhaiskasvatuspaatokset/`, environment.vardaAppUrl, { lapsi: lapsiId });
  }

  createVarhaiskasvatuspaatos(varhaiskasvatuspaatosDTO: VardaVarhaiskasvatuspaatosDTO): Observable<VardaVarhaiskasvatuspaatosDTO> {
    return this.http.post(`${this.apiPath}/varhaiskasvatuspaatokset/`, varhaiskasvatuspaatosDTO);
  }

  updateVarhaiskasvatuspaatos(varhaiskasvatuspaatosDTO: VardaVarhaiskasvatuspaatosDTO): Observable<VardaVarhaiskasvatuspaatosDTO> {
    return this.http.patch(`${this.apiPath}/varhaiskasvatuspaatokset/${varhaiskasvatuspaatosDTO.id}/`, varhaiskasvatuspaatosDTO);
  }

  deleteVarhaiskasvatuspaatos(varhaiskasvatuspaatosId: number): Observable<void> {
    return this.http.delete(`${this.apiPath}/varhaiskasvatuspaatokset/${varhaiskasvatuspaatosId}/`);
  }

  // varhaiskasvatussuhteet
  getVarhaiskasvatussuhteet(varhaiskasvatuspaatosId: number): Observable<Array<VardaVarhaiskasvatussuhdeDTO>> {
    return this.http.getAllResults(
      `${this.apiPath}/varhaiskasvatussuhteet/`,
      environment.vardaAppUrl,
      { varhaiskasvatuspaatos: varhaiskasvatuspaatosId }
    );
  }

  createVarhaiskasvatussuhde(varhaiskasvatussuhdeDTO: VardaVarhaiskasvatussuhdeDTO): Observable<VardaVarhaiskasvatussuhdeDTO> {
    return this.http.post(`${this.apiPath}/varhaiskasvatussuhteet/`, varhaiskasvatussuhdeDTO);
  }

  updateVarhaiskasvatussuhde(varhaiskasvatussuhdeDTO: VardaVarhaiskasvatussuhdeDTO): Observable<VardaVarhaiskasvatussuhdeDTO> {
    return this.http.put(`${this.apiPath}/varhaiskasvatussuhteet/${varhaiskasvatussuhdeDTO.id}/`, varhaiskasvatussuhdeDTO);
  }

  deleteVarhaiskasvatussuhde(palvelussuhdeId: number): Observable<void> {
    return this.http.delete(`${this.apiPath}/varhaiskasvatussuhteet/${palvelussuhdeId}/`);
  }

  // maksutiedot
  getMaksutiedot(lapsiId: number): Observable<Array<VardaMaksutietoDTO>> {
    return this.http.getAllResults(`${this.apiPath}/maksutiedot/`, environment.vardaAppUrl, { lapsi: lapsiId });
  }

  createMaksutieto(maksutietoDTO: VardaMaksutietoSaveDTO): Observable<VardaMaksutietoDTO> {
    return this.http.post(`${this.apiPath}/maksutiedot/`, maksutietoDTO);
  }

  updateMaksutieto(maksutietoDTO: VardaMaksutietoSaveDTO): Observable<VardaMaksutietoDTO> {
    return this.http.put(`${this.apiPath}/maksutiedot/${maksutietoDTO.id}/`, maksutietoDTO);
  }

  deleteMaksutieto(maksutietoId: number): Observable<void> {
    return this.http.delete(`${this.apiPath}/maksutiedot/${maksutietoId}/`);
  }

  // tukipaatokset
  getTukipaatokset(searchFilter: TukipaatosSearchFilter): Observable<VardaPageDto<VardaTukipaatosDTO>> {
    return this.http.get(`${this.apiPath}/tukipaatokset/`, searchFilter);
  }

  saveTukipaatokset(tukipaatos: Record<string, any>): Observable<VardaPageDto<VardaTukipaatosDTO>> {
      if (tukipaatos.id) {
        return this.http.put(`${this.apiPath}/tukipaatokset/${tukipaatos.id}/`, tukipaatos);
    } else {
        return this.http.post(`${this.apiPath}/tukipaatokset/`, tukipaatos);
    }
  }

  getTukipaatosLists(): Observable<VardaTukipaatosListsDTO> {
    return this.http.get(`${this.apiPath}/tukipaatokset/lists/`);
  }

  initFormErrorList(vakajarjestajaID: number, lapsi: LapsiListDTO) {
    this.lapsiFormErrorList.next([]);
    if (lapsi.id) {
      const searchFilter = {
        page: 1,
        page_size: 100,
        search: lapsi.henkilo_oid
      };

      this.raportitService.getLapsiErrorList(vakajarjestajaID, searchFilter).subscribe(henkiloData => {
        const henkilo = henkiloData.results.find(result => result.lapsi_id === lapsi.id);
        if (henkilo?.errors) {
          this.lapsiFormErrorList.next(henkilo.errors);
        }
      });
    }
  }

  getFormErrorList(): Observable<Array<PuutteellinenErrorDTO>> {
    return this.lapsiFormErrorList.asObservable();
  }
}
