import { Injectable } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { environment } from '../../../environments/environment';
import { TyontekijaListDTO, VardaTyontekijaDTO } from '../../utilities/models/dto/varda-tyontekija-dto.model';
import { VardaTutkintoDTO } from '../../utilities/models/dto/varda-tutkinto-dto.model';
import { VardaPageDto } from '../../utilities/models/dto/varda-page-dto';
import { VardaPalvelussuhdeDTO } from '../../utilities/models/dto/varda-palvelussuhde-dto.model';
import { VardaTaydennyskoulutusDTO, VardaTaydennyskoulutusTyontekijaListDTO } from '../../utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { VardaTyoskentelypaikkaDTO } from '../../utilities/models/dto/varda-tyoskentelypaikka-dto.model';
import { VardaPoissaoloDTO } from '../../utilities/models/dto/varda-poissolo-dto.model';
import { HenkiloListDTO } from '../../utilities/models/dto/varda-henkilo-dto.model';
import { VardaTilapainenHenkiloDTO } from '../../utilities/models/dto/varda-tilapainen-henkilo-dto.model';
import { HenkiloSearchFilter } from '../../varda-main/components/varda-main-frame/henkilo-section.abstract';
import { VardaRaportitService } from './varda-raportit.service';
import { PuutteellinenErrorDTO } from '../../utilities/models/dto/varda-puutteellinen-dto.model';

@Injectable()
export class VardaHenkilostoApiService {
  private henkilostoApiPath = `${environment.vardaAppUrl}/api/henkilosto/v1`;

  private updateHenkilostoList$ = new Subject();
  private tyontekijaFormErrorList = new BehaviorSubject<Array<PuutteellinenErrorDTO>>(null);

  constructor(
    private http: LoadingHttpService,
    private raportitService: VardaRaportitService
  ) { }

  // tyontekija
  getVakajarjestajaTyontekijat(vakajarjestajaId: number, tyontekijaSearchFilter: HenkiloSearchFilter): Observable<VardaPageDto<HenkiloListDTO>> {
    return this.http.get(`${environment.vardaAppUrl}/api/ui/vakajarjestajat/${vakajarjestajaId}/tyontekija-list/`, tyontekijaSearchFilter);
  }

  createTyontekija(tyontekijaDTO: VardaTyontekijaDTO): Observable<VardaTyontekijaDTO> {
    return this.http.post(`${this.henkilostoApiPath}/tyontekijat/`, tyontekijaDTO);
  }

  deleteTyontekija(tyontekijaId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/tyontekijat/${tyontekijaId}/`);
  }

  // tutkinnot
  getTutkinnot(henkiloOid: string, vakajarjestajaOid: string): Observable<Array<VardaTutkintoDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/tutkinnot/`, environment.vardaAppUrl, { henkilo: henkiloOid, vakajarjestaja: vakajarjestajaOid });
  }

  createTutkinto(tutkintoDTO: VardaTutkintoDTO): Observable<VardaTutkintoDTO> {
    return this.http.post(`${this.henkilostoApiPath}/tutkinnot/`, tutkintoDTO);
  }

  deleteTutkinto(tutkintoId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/tutkinnot/${tutkintoId}/`);
  }

  // palvelussuhteet
  getPalvelussuhteet(tyontekijaId: number): Observable<Array<VardaPalvelussuhdeDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/palvelussuhteet/`, environment.vardaAppUrl, { tyontekija: tyontekijaId });
  }

  createPalvelussuhde(palvelussuhdeDTO: VardaPalvelussuhdeDTO): Observable<VardaPalvelussuhdeDTO> {
    return this.http.post(`${this.henkilostoApiPath}/palvelussuhteet/`, palvelussuhdeDTO);
  }

  updatePalvelussuhde(palvelussuhdeDTO: VardaPalvelussuhdeDTO): Observable<VardaPalvelussuhdeDTO> {
    return this.http.put(`${this.henkilostoApiPath}/palvelussuhteet/${palvelussuhdeDTO.id}/`, palvelussuhdeDTO);
  }

  deletePalvelussuhde(palvelussuhdeId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/palvelussuhteet/${palvelussuhdeId}/`);
  }

  // tyoskentelypaikat
  getTyoskentelypaikat(palvelussuhdeId: number): Observable<Array<VardaTyoskentelypaikkaDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/tyoskentelypaikat/`, environment.vardaAppUrl, { palvelussuhde: palvelussuhdeId });
  }

  createTyoskentelypaikka(tyoskentelypaikkaDTO: VardaTyoskentelypaikkaDTO): Observable<VardaTyoskentelypaikkaDTO> {
    return this.http.post(`${this.henkilostoApiPath}/tyoskentelypaikat/`, tyoskentelypaikkaDTO);
  }

  updateTyoskentelypaikka(tyoskentelypaikkaDTO: VardaTyoskentelypaikkaDTO): Observable<VardaTyoskentelypaikkaDTO> {
    return this.http.put(`${this.henkilostoApiPath}/tyoskentelypaikat/${tyoskentelypaikkaDTO.id}/`, tyoskentelypaikkaDTO);
  }

  deleteTyoskentelypaikka(tyoskentelypaikkaId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/tyoskentelypaikat/${tyoskentelypaikkaId}/`);
  }

  // poissaolot
  getPoissaolot(palvelussuhdeId: number): Observable<Array<VardaPoissaoloDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/pidemmatpoissaolot/`, environment.vardaAppUrl, { palvelussuhde: palvelussuhdeId });
  }

  createPoissaolo(poissaoloDTO: VardaPoissaoloDTO): Observable<VardaPoissaoloDTO> {
    return this.http.post(`${this.henkilostoApiPath}/pidemmatpoissaolot/`, poissaoloDTO);
  }

  updatePoissaolo(poissaoloDTO: VardaPoissaoloDTO): Observable<VardaPoissaoloDTO> {
    return this.http.put(`${this.henkilostoApiPath}/pidemmatpoissaolot/${poissaoloDTO.id}/`, poissaoloDTO);
  }

  deletePoissaolo(poissaoloId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/pidemmatpoissaolot/${poissaoloId}/`);
  }

  // täydennyskoulutukset
  getTaydennyskoulutukset(searchParams: object): Observable<Array<VardaTaydennyskoulutusDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/taydennyskoulutukset/`, environment.vardaAppUrl, searchParams);
  }

  createTaydennyskoulutus(taydennyskoulutusDTO: VardaTaydennyskoulutusDTO): Observable<VardaTaydennyskoulutusDTO> {
    return this.http.post(`${this.henkilostoApiPath}/taydennyskoulutukset/`, taydennyskoulutusDTO);
  }

  updateTaydennyskoulutus(taydennyskoulutusDTO: VardaTaydennyskoulutusDTO): Observable<VardaTaydennyskoulutusDTO> {
    return this.http.put(`${this.henkilostoApiPath}/taydennyskoulutukset/${taydennyskoulutusDTO.id}/`, taydennyskoulutusDTO);
  }

  deleteTaydennyskoulutus(taydennyskoulutusId: number): Observable<void> {
    return this.http.delete(`${this.henkilostoApiPath}/taydennyskoulutukset/${taydennyskoulutusId}/`);
  }

  getTaydennyskoulutuksetTyontekijat(searchParams: object): Observable<Array<VardaTaydennyskoulutusTyontekijaListDTO>> {
    return this.http.getAllResults(`${this.henkilostoApiPath}/taydennyskoulutukset/tyontekija-list/`, environment.vardaAppUrl, searchParams);
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
