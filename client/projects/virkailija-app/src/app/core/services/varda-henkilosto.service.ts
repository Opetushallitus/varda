import { Injectable } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { VardaToimipaikkaMinimalDto } from '../../utilities/models/dto/varda-toimipaikka-dto.model';
import { Observable, Subject, EMPTY, BehaviorSubject } from 'rxjs';
import { environment } from '../../../environments/environment';
import { VardaTyontekijaDTO } from '../../utilities/models/dto/varda-tyontekija-dto.model';
import { VardaTutkintoDTO } from '../../utilities/models/dto/varda-tutkinto-dto.model';
import { VardaPageDto } from '../../utilities/models/dto/varda-page-dto';
import { VardaPalvelussuhdeDTO } from '../../utilities/models/dto/varda-palvelussuhde-dto.model';
import { VardaTaydennyskoulutusDTO, VardaTaydennyskoulutusTyontekijaListDTO } from '../../utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { VardaTyoskentelypaikkaDTO } from '../../utilities/models/dto/varda-tyoskentelypaikka-dto.model';
import { VardaPoissaoloDTO } from '../../utilities/models/dto/varda-poissolo-dto.model';
import { HenkiloListDTO } from '../../utilities/models/dto/varda-henkilo-dto.model';
import { expand, reduce, last, map } from 'rxjs/operators';
import { VardaTilapainenHenkiloDTO } from '../../utilities/models/dto/varda-tilapainen-henkilo-dto.model';

@Injectable()
export class VardaHenkilostoApiService {

  private henkilostoApiPath = `${environment.vardaAppUrl}/api/henkilosto/v1`;
  private updateHenkilostoList$ = new Subject();
  constructor(private http: LoadingHttpService) { }


  // tyontekija
  getVakajarjestajaTyontekijat(vakajarjestajaId: string, tyontekijaSearchFilter: any): Observable<VardaPageDto<HenkiloListDTO>> {
    return this.http.get(`${environment.vardaAppUrl}/api/ui/vakajarjestajat/${vakajarjestajaId}/tyontekija-list/`, tyontekijaSearchFilter);
  }

  getTyontekija(tyontekijaId: number) {
    return this.http.get(`${this.henkilostoApiPath}/tyontekijat/${tyontekijaId}/`);
  }

  createTyontekija(tyontekijaDTO: VardaTyontekijaDTO): Observable<VardaTyontekijaDTO> {
    return this.http.post(`${this.henkilostoApiPath}/tyontekijat/`, tyontekijaDTO);
  }

  deleteTyontekija(tyontekijaId: number) {
    return this.http.delete(`${this.henkilostoApiPath}/tyontekijat/${tyontekijaId}/`);
  }


  // tutkinnot
  getTutkinto(tutkintoId: number): Observable<VardaTutkintoDTO> {
    return this.http.get(`${this.henkilostoApiPath}/tutkinnot/${tutkintoId}/`);
  }
  getTutkinnot(henkiloOid: string): Observable<Array<VardaTutkintoDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/tutkinnot/`, { henkilo: henkiloOid });
  }

  createTutkinto(tutkintoDTO: VardaTutkintoDTO): Observable<VardaTutkintoDTO> {
    return this.http.post(`${this.henkilostoApiPath}/tutkinnot/`, tutkintoDTO);
  }

  deleteTutkinto(tutkintoId: number) {
    return this.http.delete(`${this.henkilostoApiPath}/tutkinnot/${tutkintoId}/`);
  }



  // palvelussuhteet
  getPalvelussuhteet(tyontekijaId: number): Observable<Array<VardaPalvelussuhdeDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/palvelussuhteet/`, { tyontekija: tyontekijaId });
  }

  createPalvelussuhde(palvelussuhdeDTO: VardaPalvelussuhdeDTO): Observable<VardaPalvelussuhdeDTO> {
    return this.http.post(`${this.henkilostoApiPath}/palvelussuhteet/`, palvelussuhdeDTO);
  }

  updatePalvelussuhde(palvelussuhdeDTO: VardaPalvelussuhdeDTO): Observable<VardaPalvelussuhdeDTO> {
    return this.http.put(`${this.henkilostoApiPath}/palvelussuhteet/${palvelussuhdeDTO.id}/`, palvelussuhdeDTO);
  }

  deletePalvelussuhde(palvelussuhdeId: number): Observable<any> {
    return this.http.delete(`${this.henkilostoApiPath}/palvelussuhteet/${palvelussuhdeId}/`);
  }



  // tyoskentelypaikat
  getTyoskentelypaikat(palvelussuhdeId: number): Observable<Array<VardaTyoskentelypaikkaDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/tyoskentelypaikat/`, { palvelussuhde: palvelussuhdeId });
  }

  createTyoskentelypaikka(tyoskentelypaikkaDTO: VardaTyoskentelypaikkaDTO): Observable<VardaTyoskentelypaikkaDTO> {
    return this.http.post(`${this.henkilostoApiPath}/tyoskentelypaikat/`, tyoskentelypaikkaDTO);
  }

  updateTyoskentelypaikka(tyoskentelypaikkaDTO: VardaTyoskentelypaikkaDTO): Observable<VardaTyoskentelypaikkaDTO> {
    return this.http.put(`${this.henkilostoApiPath}/tyoskentelypaikat/${tyoskentelypaikkaDTO.id}/`, tyoskentelypaikkaDTO);
  }

  deleteTyoskentelypaikka(tyoskentelypaikkaId: number): Observable<any> {
    return this.http.delete(`${this.henkilostoApiPath}/tyoskentelypaikat/${tyoskentelypaikkaId}/`);
  }



  // poissaolot
  getPoissaolot(palvelussuhdeId: number): Observable<Array<VardaPoissaoloDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/pidemmatpoissaolot/`, { palvelussuhde: palvelussuhdeId });
  }

  createPoissaolo(poissaoloDTO: VardaPoissaoloDTO): Observable<VardaPoissaoloDTO> {
    return this.http.post(`${this.henkilostoApiPath}/pidemmatpoissaolot/`, poissaoloDTO);
  }

  updatePoissaolo(poissaoloDTO: VardaPoissaoloDTO): Observable<VardaPoissaoloDTO> {
    return this.http.put(`${this.henkilostoApiPath}/pidemmatpoissaolot/${poissaoloDTO.id}/`, poissaoloDTO);
  }

  deletePoissaolo(poissaoloId: number): Observable<any> {
    return this.http.delete(`${this.henkilostoApiPath}/pidemmatpoissaolot/${poissaoloId}/`);
  }



  // täydennyskoulutukset
  getTaydennyskoulutukset(searchParams: object): Observable<Array<VardaTaydennyskoulutusDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/taydennyskoulutukset/`, searchParams);
  }

  createTaydennyskoulutus(taydennyskoulutusDTO: VardaTaydennyskoulutusDTO): Observable<VardaTaydennyskoulutusDTO> {
    return this.http.post(`${this.henkilostoApiPath}/taydennyskoulutukset/`, taydennyskoulutusDTO);
  }

  updateTaydennyskoulutus(taydennyskoulutusDTO: VardaTaydennyskoulutusDTO): Observable<VardaTaydennyskoulutusDTO> {
    return this.http.put(`${this.henkilostoApiPath}/taydennyskoulutukset/${taydennyskoulutusDTO.id}/`, taydennyskoulutusDTO);
  }

  deleteTaydennyskoulutus(taydennyskoulutusId: number): Observable<any> {
    return this.http.delete(`${this.henkilostoApiPath}/taydennyskoulutukset/${taydennyskoulutusId}/`);
  }

  getTaydennyskoulutuksetTyontekijat(searchParams: object): Observable<Array<VardaTaydennyskoulutusTyontekijaListDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/taydennyskoulutukset/tyontekija-list/`, searchParams);
  }


  // tilapäinen henkilöstö
  getTilapainenHenkilostoByYear(year: number, vakajarjestaja_oid: string): Observable<VardaPageDto<VardaTilapainenHenkiloDTO>> {
    return this.http.get(`${this.henkilostoApiPath}/tilapainen-henkilosto/?vuosi=${year}&vakajarjestaja=${vakajarjestaja_oid}`);
  }

  saveTilapainenHenkilostoByMonth(tilapainenHenkilostoByMonth: VardaTilapainenHenkiloDTO): Observable<any> {
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

}
