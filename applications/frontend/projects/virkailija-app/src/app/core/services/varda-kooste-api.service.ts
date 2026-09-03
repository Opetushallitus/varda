import { Injectable } from '@angular/core';
import { environment } from 'projects/virkailija-app/src/environments/environment';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { LoadingHttpService } from 'varda-shared';
import {
  LapsiByToimipaikkaDTO,
  LapsiKooste, LapsiKoosteRaw,
  TyontekijaByToimipaikkaDTO,
  TyontekijaKooste,
  TyontekijaKoosteRaw
} from '../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaPageDto } from '../../utilities/models/dto/varda-page-dto';
import { ToimipaikkaKooste, VardaToimipaikkaMinimalDto } from '../../utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaVakajarjestajaYhteenvetoDTO } from '../../utilities/models/dto/varda-vakajarjestaja-yhteenveto-dto.model';
import { VardaUtilityService } from './varda-utility.service';

@Injectable()
export class VardaKoosteApiService {

  constructor(
    private http: LoadingHttpService,
    private vardaUtilityService: VardaUtilityService,
  ) { }

  getYhteenveto(vakajarjestajaId: number): Observable<VardaVakajarjestajaYhteenvetoDTO> {
    const url = `${environment.vardaApiUrl}/vakajarjestajat/${vakajarjestajaId}/yhteenveto/`;
    return this.http.get(url);
  }

  getToimipaikkaKooste(id: number): Observable<ToimipaikkaKooste> {
    return this.http.get(`${environment.vardaV2ApiUrl}/toimipaikat/${id}/kooste/`);
  }

  getTyontekijaKooste(id: number, getReadOnlyTaydennyskoulutus = false): Observable<TyontekijaKooste> {
    return this.http.get(`${environment.vardaAppUrl}/api/henkilosto/v1/tyontekijat/${id}/kooste/`).pipe(
      map((result: TyontekijaKoosteRaw) => {
        const taydennyskoulutusList = [];
        // Combine TaydennyskoulutusTyontekija objects by ID
        result.taydennyskoulutukset.forEach(taydennyskoulutus => {
          if (taydennyskoulutus.read_only && !getReadOnlyTaydennyskoulutus) {
            // If Taydennyskoulutus is read_only, do not include it in results (e.g. katsele tietoja)
            return;
          }
          const existingTaydennyskoulutus = taydennyskoulutusList.find(tk => tk.id === taydennyskoulutus.id);
          if (existingTaydennyskoulutus) {
            existingTaydennyskoulutus.tehtavanimikeList.push(taydennyskoulutus.tehtavanimike_koodi);
          } else {
            taydennyskoulutusList.push({
              ...taydennyskoulutus,
              tehtavanimikeList: [taydennyskoulutus.tehtavanimike_koodi]
            });
          }
        });
        return {...result, taydennyskoulutukset: taydennyskoulutusList};
      })
    );
  }

  getLapsiKooste(id: number): Observable<LapsiKooste> {
    return this.http.get(`${environment.vardaApiUrl}/lapset/${id}/kooste/`).pipe(
      map((result: LapsiKoosteRaw) => {
        const varhaiskasvatuspaatosList = result.varhaiskasvatuspaatokset.map(varhaiskasvatuspaatos => (
          {...varhaiskasvatuspaatos,
            varhaiskasvatussuhteet: result.varhaiskasvatussuhteet.filter(varhaiskasvatussuhde =>
              varhaiskasvatuspaatos.id.toString() === this.vardaUtilityService.parseIdFromUrl(varhaiskasvatussuhde.varhaiskasvatuspaatos))}
        ));
        const newResult = {...result, varhaiskasvatuspaatokset: varhaiskasvatuspaatosList};
        delete newResult.varhaiskasvatussuhteet;
        return newResult;
      })
    );
  }

  getToimipaikatForVakajarjestaja(vakajarjestajaId: number, searchParams?: any): Observable<VardaPageDto<VardaToimipaikkaMinimalDto>> {
    let url = `${environment.vardaAppUrl}/api/ui/vakajarjestajat/${vakajarjestajaId}/toimipaikat/`;

    if (searchParams) {
      url = this.vardaUtilityService.parseSearchParams(url, searchParams);
    }

    return this.http.get(url);
  }

  getTyontekijatForVakajarjestaja(
    vakajarjestajaId: number,
    searchParams: any
  ): Observable<VardaPageDto<TyontekijaByToimipaikkaDTO>> {
    let url = `${environment.vardaAppUrl}/api/ui/vakajarjestajat/${vakajarjestajaId}/tyontekijat/`;
    url = this.vardaUtilityService.parseSearchParams(url, searchParams);

    return this.http.get(url);
  }

  getLapsetForVakajarjestaja(
    vakajarjestajaId: number,
    searchParams?: any
  ): Observable<VardaPageDto<LapsiByToimipaikkaDTO>> {
    let url = `${environment.vardaAppUrl}/api/ui/vakajarjestajat/${vakajarjestajaId}/lapset/`;

    if (searchParams) {
      url = this.vardaUtilityService.parseSearchParams(url, searchParams);
    }

    return this.http.get(url);
  }
}
