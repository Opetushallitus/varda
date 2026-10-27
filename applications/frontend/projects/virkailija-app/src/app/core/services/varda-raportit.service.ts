import { Injectable } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { BehaviorSubject, Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { YksiloimatonSearchFilter, VardaYksiloimatonDTO } from '../../utilities/models/dto/varda-yksiloimaton-dto.model';
import { VardaPageDto } from '../../utilities/models/dto/varda-page-dto';
import { HenkiloListDTO } from '../../utilities/models/dto/varda-henkilo-dto.model';
import { PuutteellinenSearchFilter } from '../../varda-main/components/varda-raportit/varda-puutteelliset-tiedot/abstract-puutteelliset.component';
import { VardaTiedonsiirtoDTO, VardaTiedonsiirtoYhteenvetoDTO } from '../../utilities/models/dto/varda-tiedonsiirto-dto.model';
import { VardaExcelReportDTO, VardaExcelReportPostDTO } from '../../utilities/models/dto/varda-excel-report-dto.model';
import {
  PuutteellinenErrorsDTO,
  PuutteellinenOrganisaatioListDTO,
  PuutteellinenToimipaikkaListDTO
} from '../../utilities/models/dto/varda-puutteellinen-dto.model';
import { TransferOutage } from '../../utilities/models/dto/varda-transfer-outage-dto.model';
import { VardaPaginatorParams } from '../../utilities/models/varda-paginator-params.model';
import { RequestSummary } from '../../utilities/models/dto/varda-request-summary-dto.model';

@Injectable()
export class VardaRaportitService {
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

  getLapsiErrors(vakajarjestajaId: number): Observable<PuutteellinenErrorsDTO> {
    return this.http.get(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/error-report-lapset/error_codes/`);
  }

  getTyontekijaErrorList(vakajarjestajaId: number, searchFilter: PuutteellinenSearchFilter): Observable<VardaPageDto<HenkiloListDTO>> {
    return this.http.get(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/error-report-tyontekijat/`, searchFilter);
  }

  getTyontekijatErrors(vakajarjestajaId: number): Observable<PuutteellinenErrorsDTO> {
    return this.http.get(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/error-report-tyontekijat/error_codes/`);
  }

  getToimipaikkaErrorList(
    vakajarjestajaId: number, searchFilter: PuutteellinenSearchFilter
  ): Observable<VardaPageDto<PuutteellinenToimipaikkaListDTO>> {
    return this.http.get(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/error-report-toimipaikat/`, searchFilter);
  }

  getToimipaikkaErrors(vakajarjestajaId: number): Observable<PuutteellinenErrorsDTO> {
    return this.http.get(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/error-report-toimipaikat/error_codes/`);
  }

  getOrganisaatioErrorList(
    organisaatioId: number, searchFilter: PuutteellinenSearchFilter
  ): Observable<VardaPageDto<PuutteellinenOrganisaatioListDTO>> {
    return this.http.get(`${this.apiPath}/vakajarjestajat/${organisaatioId}/error-report-organisaatio/`, searchFilter);
  }

  getOrganisaatioErrors(vakajarjestajaId: number): Observable<PuutteellinenErrorsDTO> {
    return this.http.get(`${this.apiPath}/vakajarjestajat/${vakajarjestajaId}/error-report-organisaatio/error_codes/`);
  }

  setSelectedVakajarjestajat(selectedVakajarjestajat: Array<number>) {
    this.selectedVakajarjestajat$.next(selectedVakajarjestajat);
  }

  getSelectedVakajarjestajat() {
    return this.selectedVakajarjestajat$.asObservable();
  }

  getExcelReportList(vakajarjestajaId: number, searchParams: VardaPaginatorParams): Observable<VardaPageDto<VardaExcelReportDTO>> {
    return this.http.get(`${this.reportingApi}/v1/excel-reports/?organisaatio=${vakajarjestajaId}`, searchParams);
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

  getReminderReport(start_date, end_date): Observable<Blob> {
  return this.http.get(
    `${this.adminApiPath}/get-muistutus-report/alkupvm=${start_date}/loppupvm=${end_date}/`,
    undefined,
    undefined,
    {responseType: 'blob'}
  );
  }
}
