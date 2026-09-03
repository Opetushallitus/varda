import { Injectable } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { Observable } from 'rxjs';
import { environment } from 'projects/virkailija-app/src/environments/environment';
import { PaosToimintaCreateDto, PaosToimintaDto, PaosToimintatietoDto, PaosToimipaikkaDto, PaosToimipaikkatietoDto, PaosVakajarjestajaDto } from '../../utilities/models/dto/varda-paos-dto';
import { VardaApiService } from './varda-api.service';
import { AllVakajarjestajaSearchDto } from '../../utilities/models/varda-vakajarjestaja.model';
import { VardaVakajarjestajaUi } from '../../utilities/models';

@Injectable()
export class VardaPaosApiService {
  private apiPath = `${environment.vardaAppUrl}/api/v1`;
  private uiPath = `${environment.vardaAppUrl}/api/ui`;

  constructor(private http: LoadingHttpService) { }

  getPaosToimipaikat(vakajarjestajaId: number): Observable<Array<PaosToimipaikkatietoDto>> {
    return this.http.getAllResults(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/paos-toimipaikat/`, environment.vardaAppUrl);
  }

  getPaosToimijat(vakajarjestajaId: number): Observable<Array<PaosToimintatietoDto>> {
    return this.http.getAllResults(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/paos-toimijat/`, environment.vardaAppUrl);
  }

  getAllPaosToimijat(searchDto: AllVakajarjestajaSearchDto): Observable<Array<PaosVakajarjestajaDto>> {
    const url = `${this.uiPath}/all-vakajarjestajat/`;
    return this.http.getAllResults(url, environment.vardaAppUrl, searchDto);
  }

  getAllPaosToimipaikat(id: number, searchDto: Record<string, any>): Observable<Array<PaosToimipaikkaDto>> {
    const url = `${this.uiPath}/vakajarjestajat/${id}/all-toimipaikat/`;
    return this.http.getAllResults(url, environment.vardaAppUrl, searchDto);
  }

  createPaosToiminta(createDto: PaosToimintaCreateDto): Observable<PaosToimintaDto> {
    const url = `${environment.vardaApiUrl}/paos-toiminnat/`;
    return this.http.post(url, createDto);
  }

  getPaosJarjestajat(vakajarjestajaId: number, toimipaikkaId: number): Observable<Array<VardaVakajarjestajaUi>> {
    const url = `${this.uiPath}/vakajarjestajat/${vakajarjestajaId}/toimipaikat/${toimipaikkaId}/paos-jarjestajat/`;
    return this.http.getAllResults(url, environment.vardaAppUrl);
  }

   deletePaosToiminta(paostoimintaId: string): Observable<void> {
    const url = `${environment.vardaApiUrl}/paos-toiminnat/${paostoimintaId}/`;
    return this.http.delete(url);
  }

  updatePaosOikeus(paosOikeusId: number, savingToimijaId: number): Observable<void> {
    const url = `${environment.vardaApiUrl}/paos-oikeudet/${paosOikeusId}/`;
    const savingToimijaUrl = VardaApiService.getVakajarjestajaUrlFromId(savingToimijaId);
    return this.http.put(url, { tallentaja_organisaatio: savingToimijaUrl });
  }
}
