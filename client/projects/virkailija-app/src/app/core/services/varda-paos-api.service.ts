import { Injectable } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { Observable, Subject } from 'rxjs';
import { environment } from 'projects/virkailija-app/src/environments/environment';
import { PaosToimintatietoDto, PaosToimipaikkatietoDto } from '../../utilities/models/dto/varda-paos-dto';



@Injectable()
export class VardaPaosApiService {

  private apiPath = `${environment.vardaAppUrl}/api/v1`;
  private apiUiPath = `${environment.vardaAppUrl}/api/ui`;

  constructor(private http: LoadingHttpService) { }


  getPaosToimipaikat(vakajarjestajaId: string): Observable<Array<PaosToimipaikkatietoDto>> {
    return this.http.getAllResults(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/paos-toimipaikat/`, environment.vardaAppUrl);
  }

  getPaosToimijat(vakajarjestajaId: string): Observable<Array<PaosToimintatietoDto>> {
    return this.http.getAllResults(`${this.apiPath}/${vakajarjestajaId}/paos-toimijat/`, environment.vardaAppUrl);
  }

}
