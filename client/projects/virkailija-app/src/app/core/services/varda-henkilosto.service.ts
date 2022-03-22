import { Injectable } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  TyontekijaListDTO, VardaPalvelussuhdeDTO, VardaPidempiPoissaoloDTO,
  VardaTutkintoDTO,
  VardaTyontekijaDTO, VardaTyoskentelypaikkaDTO
} from '../../utilities/models/dto/varda-tyontekija-dto.model';
import { VardaPageDto } from '../../utilities/models/dto/varda-page-dto';
import { VardaTaydennyskoulutusDTO, VardaTaydennyskoulutusTyontekijaListDTO } from '../../utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { HenkiloListDTO } from '../../utilities/models/dto/varda-henkilo-dto.model';
import { VardaTilapainenHenkiloDTO } from '../../utilities/models/dto/varda-tilapainen-henkilo-dto.model';
import { HenkiloSearchFilter } from '../../varda-main/components/varda-main-frame/henkilo-section.abstract';
import { VardaRaportitService } from './varda-raportit.service';
import { PuutteellinenErrorDTO } from '../../utilities/models/dto/varda-puutteellinen-dto.model';
import { TyontekijaKooste } from '../../utilities/models/dto/varda-henkilohaku-dto.model';

@Injectable()
export class VardaHenkilostoApiService {
  activeTyontekija = new BehaviorSubject<TyontekijaKooste>(null);
  tutkintoChanged = new BehaviorSubject<boolean>(true);
  tyoskentelypaikkaChanged = new BehaviorSubject<boolean>(true);

  private henkilostoApiPath = `${environment.vardaAppUrl}/api/henkilosto/v1`;
  private updateHenkilostoList$ = new Subject();
  private tyontekijaFormErrorList = new BehaviorSubject<Array<PuutteellinenErrorDTO>>(null);

  constructor(
    private http: LoadingHttpService,
    private raportitService: VardaRaportitService
  ) { }

  getTyontekijaUrl(id: number) {
    return `/api/henkilosto/v1/tyontekijat/${id}/`;
  }

  getPalvelussuhdeUrl(id: number) {
    return `/api/henkilosto/v1/palvelussuhteet/${id}/`;
  }

  // tyontekija
  getVakajarjestajaTyontekijat(vakajarjestajaId: number, tyontekijaSearchFilter: HenkiloSearchFilter): Observable<VardaPageDto<HenkiloListDTO>> {
    return this.http.get(`${environment.vardaAppUrl}/api/ui/vakajarjestajat/${vakajarjestajaId}/tyontekija-list/`, tyontekijaSearchFilter);
  }

  createTyontekija(tyontekijaDTO: Record<string, any>): Observable<VardaTyontekijaDTO> {
    return this.http.post(`${this.henkilostoApiPath}/tyontekijat/`, tyontekijaDTO);
  }

  deleteTyontekija(tyontekijaId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/tyontekijat/${tyontekijaId}/`);
  }

  // tutkinnot
  createTutkinto(tutkintoDTO: Record<string, any>): Observable<VardaTutkintoDTO> {
    return this.http.post(`${this.henkilostoApiPath}/tutkinnot/`, tutkintoDTO);
  }

  deleteTutkinto(tutkintoId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/tutkinnot/${tutkintoId}/`);
  }

  // palvelussuhteet
  createPalvelussuhde(palvelussuhdeDTO: Record<string, any>): Observable<VardaPalvelussuhdeDTO> {
    return this.http.post(`${this.henkilostoApiPath}/palvelussuhteet/`, palvelussuhdeDTO);
  }

  updatePalvelussuhde(palvelussuhdeDTO: Record<string, any>): Observable<VardaPalvelussuhdeDTO> {
    return this.http.put(`${this.henkilostoApiPath}/palvelussuhteet/${palvelussuhdeDTO.id}/`, palvelussuhdeDTO);
  }

  deletePalvelussuhde(palvelussuhdeId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/palvelussuhteet/${palvelussuhdeId}/`);
  }

  // tyoskentelypaikat
  createTyoskentelypaikka(tyoskentelypaikkaDTO: Record<string, any>): Observable<VardaTyoskentelypaikkaDTO> {
    return this.http.post(`${this.henkilostoApiPath}/tyoskentelypaikat/`, tyoskentelypaikkaDTO);
  }

  updateTyoskentelypaikka(tyoskentelypaikkaDTO: Record<string, any>): Observable<VardaTyoskentelypaikkaDTO> {
    return this.http.put(`${this.henkilostoApiPath}/tyoskentelypaikat/${tyoskentelypaikkaDTO.id}/`, tyoskentelypaikkaDTO);
  }

  deleteTyoskentelypaikka(tyoskentelypaikkaId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/tyoskentelypaikat/${tyoskentelypaikkaId}/`);
  }

  // poissaolot
  createPoissaolo(poissaoloDTO: Record<string, any>): Observable<VardaPidempiPoissaoloDTO> {
    return this.http.post(`${this.henkilostoApiPath}/pidemmatpoissaolot/`, poissaoloDTO);
  }

  updatePoissaolo(poissaoloDTO: Record<string, any>): Observable<VardaPidempiPoissaoloDTO> {
    return this.http.put(`${this.henkilostoApiPath}/pidemmatpoissaolot/${poissaoloDTO.id}/`, poissaoloDTO);
  }

  deletePoissaolo(poissaoloId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/pidemmatpoissaolot/${poissaoloId}/`);
  }

  // täydennyskoulutukset
  getTaydennyskoulutukset(searchParams: Record<string, unknown>): Observable<Array<VardaTaydennyskoulutusDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/taydennyskoulutukset/`, environment.vardaAppUrl, searchParams);
  }

  createTaydennyskoulutus(taydennyskoulutusDTO: Record<string, any>): Observable<VardaTaydennyskoulutusDTO> {
    return this.http.post(`${this.henkilostoApiPath}/taydennyskoulutukset/`, taydennyskoulutusDTO);
  }

  updateTaydennyskoulutus(taydennyskoulutusDTO: Record<string, any>): Observable<VardaTaydennyskoulutusDTO> {
    return this.http.put(`${this.henkilostoApiPath}/taydennyskoulutukset/${taydennyskoulutusDTO.id}/`, taydennyskoulutusDTO);
  }

  deleteTaydennyskoulutus(taydennyskoulutusId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/taydennyskoulutukset/${taydennyskoulutusId}/`);
  }

  getTaydennyskoulutuksetTyontekijat(searchParams: Record<string, unknown>): Observable<Array<VardaTaydennyskoulutusTyontekijaListDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/taydennyskoulutukset/tyontekija-list/`, environment.vardaAppUrl, searchParams);
  }

  // tilapäinen henkilöstö
  getTilapainenHenkilostoByYear(year: number, vakajarjestaja_oid: string): Observable<VardaPageDto<VardaTilapainenHenkiloDTO>> {
    return this.http.get(`${this.henkilostoApiPath}/tilapainen-henkilosto/?vuosi=${year}&vakajarjestaja=${vakajarjestaja_oid}`);
  }

  saveTilapainenHenkilostoByMonth(tilapainenHenkilostoByMonth: Record<string, any>): Observable<VardaTilapainenHenkiloDTO> {
    if (tilapainenHenkilostoByMonth.url) {
      return this.http.put(`${this.henkilostoApiPath}/tilapainen-henkilosto/${tilapainenHenkilostoByMonth.id}/`, tilapainenHenkilostoByMonth);
    } else {
      return this.http.post(`${this.henkilostoApiPath}/tilapainen-henkilosto/`, tilapainenHenkilostoByMonth);
    }
  }

  // listeners
  listenHenkilostoListUpdate(): Observable<any> {
    return this.updateHenkilostoList$.asObservable();
  }

  sendHenkilostoListUpdate() {
    this.updateHenkilostoList$.next(true);
  }

  initFormErrorList(vakajarjestajaID: number, tyontekija: TyontekijaListDTO) {
    this.tyontekijaFormErrorList.next([]);
    if (tyontekija.id) {
      const searchFilter = {
        page: 1,
        page_size: 100,
        search: tyontekija.henkilo_oid
      };

      this.raportitService.getTyontekijaErrorList(vakajarjestajaID, searchFilter).subscribe(henkiloData => {
        const henkilo = henkiloData.results.find(result => result.tyontekija_id === tyontekija.id);
        if (henkilo?.errors) {
          this.tyontekijaFormErrorList.next(henkilo.errors);
        }
      });
    }
  }

  getFormErrorList(): Observable<Array<PuutteellinenErrorDTO>> {
    return this.tyontekijaFormErrorList.asObservable();
  }
}
