import { Observable } from 'rxjs';
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

import { LoadingHttpService } from 'varda-shared';
import { VardaPageDto } from '../../utilities/models/dto/varda-page-dto';
import { VardaTilapainenHenkiloDTO } from '../../utilities/models/dto/varda-tilapainen-henkilo-dto.model';


@Injectable()
export class VardaHenkilostoService {
  private henkilostoApiPath = `${environment.vardaAppUrl}/api/henkilosto/v1`;

  constructor(private http: LoadingHttpService) { }

  getTilapainenHenkilostoByYear(year: number, vakajarjestaja_oid: string): Observable<VardaPageDto<VardaTilapainenHenkiloDTO>> {
    return this.http.get(`${this.henkilostoApiPath}/tilapainen-henkilosto/?vuosi=${year}&vakajarjestaja=${vakajarjestaja_oid}`);
  }


  saveTilapainenHenkilostoByMonth(tilapainenHenkilostoByMonth: VardaTilapainenHenkiloDTO): Observable<any> {
    if (tilapainenHenkilostoByMonth.url) {
      return this.http.put(tilapainenHenkilostoByMonth.url, tilapainenHenkilostoByMonth);
    } else {
      return this.http.post(`${this.henkilostoApiPath}/tilapainen-henkilosto/`, tilapainenHenkilostoByMonth);
    }
  }

}
