import { Injectable } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { YksiloimatonSearchFilter, VardaYksiloimatonDTO } from '../../utilities/models/dto/varda-yksiloimaton-dto.model';
import { VardaPageDto } from '../../utilities/models/dto/varda-page-dto';
import { HenkiloListDTO } from '../../utilities/models/dto/varda-henkilo-dto.model';
import { PuutteellinenSearchFilter } from '../../varda-main/components/varda-raportit/varda-puutteelliset-tiedot/abstract-puutteelliset.component';
import { VardaTiedonsiirtoDTO, VardaTiedonsiirtoYhteenvetoDTO } from '../../utilities/models/dto/varda-tiedonsiirto-dto.model';
import { TiedonsiirrotSearchFilter } from '../../varda-main/components/varda-raportit/varda-tiedonsiirrot/tiedonsiirrot-sections.abstract';
import { catchError } from 'rxjs/operators';
import { of } from 'rxjs';
import { VardaExcelReportDTO, VardaExcelReportPostDTO } from '../../utilities/models/dto/varda-excel-report-dto.model';
import { PuutteellinenToimipaikkaListDTO } from '../../utilities/models/dto/varda-puutteellinen-dto.model';
import { TransferOutage } from '../../utilities/models/dto/varda-transfer-outage-dto.model';
import { VardaPaginatorParams } from '../../utilities/models/varda-paginator-params.model';
import { RequestSummary } from '../../utilities/models/dto/varda-request-summary-dto.model';
import {
  VardaYearlyReportDTO,
  VardaYearlyReportPostDTO
} from '../../utilities/models/dto/varda-yearly-report-dto.model';

@Injectable()
export class VardaRaportitService {
  public showPuutteellisetError$ = new BehaviorSubject<boolean>(false);
  private selectedVakajarjestajat$ = new BehaviorSubject<Array<number>>(null);
  private apiPath = `${environment.vardaAppUrl}/api/v1`;
  private adminApiPath = `${environment.vardaAppUrl}/api/admin`;
  private reportingApi = `${environment.vardaAppUrl}/api/reporting`;

  constructor(private http: LoadingHttpService) { }

  getYksiloimattomat(searchFilter: YksiloimatonSearchFilter): Observable<VardaPageDto<VardaYksiloimatonDTO>> {
    return this.http.get(`${this.adminApiPath}/hae-yksiloimattomat/`, searchFilter);
  }

  getTiedonsiirrotYhteenveto(searchFilter: Record<string, any>): Observable<VardaPageDto<VardaTiedonsiirtoYhteenvetoDTO>> {
    return this.http.get(`${this.reportingApi}/v1/tiedonsiirto/yhteenveto/`, searchFilter);
  }

  getTiedonsiirrot(searchFilter: Record<string, any>): Observable<VardaPageDto<VardaTiedonsiirtoDTO>> {
    return this.http.get(`${this.reportingApi}/v1/tiedonsiirto/`, searchFilter);
  }

  getLapsiErrorList(vakajarjestajaId: number, searchFilter: PuutteellinenSearchFilter): Observable<VardaPageDto<HenkiloListDTO>> {
    return this.http.get(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/error-report-lapset/`, searchFilter);
  }

  getTyontekijaErrorList(vakajarjestajaId: number, searchFilter: PuutteellinenSearchFilter): Observable<VardaPageDto<HenkiloListDTO>> {
    return this.http.get(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/error-report-tyontekijat/`, searchFilter);
  }

  getToimipaikkaErrorList(vakajarjestajaId: number, searchFilter: PuutteellinenSearchFilter): Observable<VardaPageDto<PuutteellinenToimipaikkaListDTO>> {
    return this.http.get(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/error-report-toimipaikat/`, searchFilter);
  }

  getPuutteellisetCount(vakajarjestajaId: number): Observable<boolean> {
    const searchFilter: PuutteellinenSearchFilter = {
      page_size: 1,
      page: 1
    };

    return new Observable(obs => {
      forkJoin([
        this.getLapsiErrorList(vakajarjestajaId, searchFilter).pipe(catchError((err: Error) => of({ count: 0 }))),
        this.getTyontekijaErrorList(vakajarjestajaId, searchFilter).pipe(catchError((err: Error) => of({ count: 0 }))),
        this.getToimipaikkaErrorList(vakajarjestajaId, searchFilter).pipe(catchError((err: Error) => of({ count: 0 })))
      ]).subscribe(([lapsiData, tyontekijaData, toimipaikkaData]) => {
        const showPuutteellisetError = lapsiData?.count > 0 || tyontekijaData?.count > 0 || toimipaikkaData?.count > 0;
        this.showPuutteellisetError$.next(showPuutteellisetError);
        obs.next(showPuutteellisetError);
        obs.complete();
      });
    });
  }

  setSelectedVakajarjestajat(selectedVakajarjestajat: Array<number>) {
    this.selectedVakajarjestajat$.next(selectedVakajarjestajat);
  }

  getSelectedVakajarjestajat() {
    return this.selectedVakajarjestajat$.asObservable();
  }

  getExcelReportList(vakajarjestajaId: number, searchParams: VardaPaginatorParams): Observable<VardaPageDto<VardaExcelReportDTO>> {
    return this.http.get(`${this.reportingApi}/v1/excel-reports/?vakajarjestaja=${vakajarjestajaId}`, searchParams);
  }

  getExcelReport(reportId: number): Observable<VardaExcelReportDTO> {
    return this.http.get(`${this.reportingApi}/v1/excel-reports/${reportId}/`);
  }

  postExcelReport(report: VardaExcelReportPostDTO) {
    return this.http.post(`${this.reportingApi}/v1/excel-reports/`, report);
  }

  downloadExcelReport(url: string): Observable<any> {
    return this.http.get(url, undefined, undefined, {responseType: 'arraybuffer'});
  }

  getTransferOutage(searchFilter: Record<string, unknown>): Observable<VardaPageDto<TransferOutage>> {
    return this.http.get(`${this.reportingApi}/v1/transfer-outage/`, searchFilter);
  }

  getRequestSummary(searchFilter: Record<string, unknown>): Observable<VardaPageDto<RequestSummary>> {
    return this.http.get(`${this.reportingApi}/v1/request-summary/`, searchFilter);
  }

  postYearlyReport(report: VardaYearlyReportPostDTO): Observable<VardaYearlyReportDTO> {
    return this.http.post(`${this.reportingApi}/v1/yearly-reporting-summary/`, report);
  }
}
