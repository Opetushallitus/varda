import { catchError, expand, map, mergeMap, reduce } from 'rxjs/operators';
import { Injectable } from '@angular/core';
import { Observable, forkJoin, of, EMPTY } from 'rxjs';
import { FormGroup } from '@angular/forms';
import { VardaApiService } from './varda-api.service';
import { VardaVakajarjestajaService } from './varda-vakajarjestaja.service';
import { VardaUtilityService } from './varda-utility.service';
import { VardaDateService } from '../../varda-main/services/varda-date.service';
import { environment } from '../../../environments/environment';

import {
  VardaFieldSet,
  VardaWidgetNames,
  VardaHenkiloDTO,
  VardaLapsiDTO,
  VardaVarhaiskasvatussuhdeDTO,
  VardaToimipaikkaDTO,
  VardaKielipainotusDTO,
  VardaToimintapainotusDTO,
  VardaExtendedHenkiloModel,
  VardaVakajarjestaja,
  VardaVakajarjestajaUi,
  VardaVarhaiskasvatuspaatosDTO,
  VardaField,
  VardaKoodistot,
  VardaEndpoints
} from '../../utilities/models';
import { LoadingHttpService } from 'varda-shared';
import {VardaToimipaikkaYhteenvetoDTO} from '../../utilities/models/dto/varda-toimipaikka-yhteenveto-dto.model';
import {VardaFieldsetArrayContainer} from '../../utilities/models/varda-fieldset.model';
import {VardaMaksutietoDTO} from '../../utilities/models/dto/varda-maksutieto-dto.model';
import {LapsiByToimipaikkaDTO} from '../../utilities/models/dto/varda-henkilohaku-dto.model';
import {VardaPageDto} from '../../utilities/models/dto/varda-page-dto';
import {VardaToimipaikkaMinimalDto} from '../../utilities/models/dto/varda-toimipaikka-dto.model';
import {VardaLapsiCreateDto} from '../../utilities/models/dto/varda-lapsi-dto.model';

@Injectable()
export class VardaApiWrapperService {

  vardaForm: FormGroup;
  operation: string;
  entityName: string;

  constructor(
    private vardaApiService: VardaApiService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vardaDateService: VardaDateService,
    private vardaUtilityService: VardaUtilityService,
    private http: LoadingHttpService) { }

  createNewLapsi(henkilo: VardaHenkiloDTO, toimipaikka: VardaToimipaikkaDTO, suhteet: any, data: any): Observable<any> {
    const varhaiskasvatussuhdeAndPaatosData = {};

    if (suhteet.addVarhaiskasvatussuhde) {
      varhaiskasvatussuhdeAndPaatosData['varhaiskasvatussuhde'] = data.varhaiskasvatussuhde;
      varhaiskasvatussuhdeAndPaatosData['varhaiskasvatuspaatos'] = data.varhaiskasvatuspaatos;
    }

    return new Observable((observer) => {
      const extendedHenkilo: VardaExtendedHenkiloModel = {};
      extendedHenkilo.henkilo = henkilo;
      let lapsiId, paatosId, lapsiExists = false;

      this.createLapsi(data.createLapsiDto).pipe(mergeMap((lapsi) => {

        if (!lapsi) {
          observer.error(null);
          return;
        }

        extendedHenkilo.lapsi = lapsi;
        lapsiId = lapsi.id;
        lapsiExists = lapsi.varhaiskasvatuspaatokset_top.length > 0;
        extendedHenkilo.henkilo.lapsi = [lapsi.url];

        let createVarhaiskasvatussuhdeObs = of(null);
        let saveVarhaiskasvatuspaatosObs = of(null);

        if (suhteet.addVarhaiskasvatussuhde) {
          saveVarhaiskasvatuspaatosObs = this.saveVarhaiskasvatuspaatos(false, lapsi, null,
            varhaiskasvatussuhdeAndPaatosData['varhaiskasvatuspaatos']);
        }


        return forkJoin([saveVarhaiskasvatuspaatosObs]).pipe(mergeMap((paatokset) => {
          const vakapaatos = paatokset[0];
          paatosId = vakapaatos.id;

          if (vakapaatos) {
            createVarhaiskasvatussuhdeObs = this.createVarhaiskasvatussuhde(
              toimipaikka,
              paatokset[0],
              varhaiskasvatussuhdeAndPaatosData['varhaiskasvatussuhde']);
          }

          return forkJoin([createVarhaiskasvatussuhdeObs]);
        }));

      })).subscribe(() => {
        observer.next(lapsiExists ? null : extendedHenkilo);
        observer.complete();
      }, (e) => {
        observer.error(e);

        if (lapsiId) {
          if (paatosId) {
            this.deleteVarhaiskasvatuspaatos(paatosId.toString()).subscribe(() => {
              if (!lapsiExists) {
                this.deleteLapsi(lapsiId.toString()).subscribe();
              }
            });
          } else {
            if (!lapsiExists) {
              this.deleteLapsi(lapsiId.toString()).subscribe();
            }
          }
        }
      });
    });
  }

  createHenkiloByHenkiloDetails(ssnOrOid: string, firstnames: string, nickname: string, lastname: string, isSsn: boolean): Observable<any> {
    const henkiloCreateObj = {};

    henkiloCreateObj['etunimet'] = firstnames;
    henkiloCreateObj['kutsumanimi'] = nickname;
    henkiloCreateObj['sukunimi'] = lastname;
    if (isSsn) {
      henkiloCreateObj['henkilotunnus'] = ssnOrOid;
    } else {
      henkiloCreateObj['henkilo_oid'] = ssnOrOid;
    }
    return this.vardaApiService.createHenkilo(henkiloCreateObj);
  }

  createLapsi(lapsiDTO: VardaLapsiCreateDto): Observable<any> {
    return new Observable((henkiloObserver) => {
      this.vardaApiService.createLapsi(lapsiDTO).subscribe((lapsi) => {
        henkiloObserver.next(lapsi);
        henkiloObserver.complete();
      }, (e) => henkiloObserver.error(e));
    });
  }

  createVarhaiskasvatussuhde(toimipaikka: VardaToimipaikkaDTO,
    varhaiskasvatuspaatos: VardaVarhaiskasvatuspaatosDTO, data: any): Observable<any> {
    const varhaiskasvatussuhdeDTO = this.createDTOwithData<VardaVarhaiskasvatussuhdeDTO>(
      data.formData,
      new VardaVarhaiskasvatussuhdeDTO(),
      data.fieldSets);

    varhaiskasvatussuhdeDTO.varhaiskasvatuspaatos = varhaiskasvatuspaatos.url;
    varhaiskasvatussuhdeDTO.toimipaikka = toimipaikka.url;
    return this.vardaApiService.createVarhaiskasvatussuhde(varhaiskasvatussuhdeDTO);
  }

  saveToimipaikka(isEdit: boolean, toimipaikka: VardaToimipaikkaDTO, data: any): Observable<any> {
    const toimipaikkaData = data.toimipaikka;
    const toimipaikkaDTO = this.createDTOwithData<VardaToimipaikkaDTO>(
      toimipaikkaData.formData,
      new VardaToimipaikkaDTO(),
      toimipaikkaData.fieldSets);
    toimipaikkaDTO.vakajarjestaja = VardaApiService.getVakajarjestajaUrlFromId(this.vardaVakajarjestajaService.getSelectedVakajarjestajaId());
    const toimipaikkaFormDataKeys = Object.keys(toimipaikkaData.formData);
    const someKey = toimipaikkaFormDataKeys.pop();
    toimipaikkaDTO.kielipainotus_kytkin = toimipaikkaData.formData[someKey]['kielipainotus_kytkin'];
    toimipaikkaDTO.toiminnallinenpainotus_kytkin = toimipaikkaData.formData[someKey]['toiminnallinenpainotus_kytkin'];
    if (isEdit) {
      return this.vardaApiService.editToimipaikka(this.vardaUtilityService.parseIdFromUrl(toimipaikka.url), toimipaikkaDTO);
    } else {
      return this.vardaApiService.createToimipaikka(toimipaikkaDTO);
    }
  }

  saveVarhaiskasvatussuhde(
    isEdit: boolean,
    varhaiskasvatuspaatos: VardaVarhaiskasvatuspaatosDTO,
    varhaiskasvatussuhde: VardaVarhaiskasvatussuhdeDTO,
    data: any): Observable<any> {

    const varhaiskasvatussuhdeFormData = data.formData;
    const toimipaikkaReference = varhaiskasvatussuhdeFormData.toimipaikka.url;
    const varhaiskasvatuspaatosReference = varhaiskasvatussuhdeFormData.varhaiskasvatuspaatos.url;
    delete varhaiskasvatussuhdeFormData.toimipaikka;
    delete varhaiskasvatussuhdeFormData.varhaiskasvatuspaatos;
    const varhaiskasvatussuhdeDTO = this.createDTOwithData<VardaVarhaiskasvatussuhdeDTO>(
      varhaiskasvatussuhdeFormData,
      new VardaVarhaiskasvatussuhdeDTO(),
      data.fieldSets);
    varhaiskasvatussuhdeDTO.varhaiskasvatuspaatos = varhaiskasvatuspaatosReference;
    varhaiskasvatussuhdeDTO.toimipaikka = toimipaikkaReference;
    if (isEdit) {
      return this.vardaApiService.editVarhaiskasvatussuhde(
        this.vardaUtilityService.parseIdFromUrl(varhaiskasvatussuhde.url), varhaiskasvatussuhdeDTO);
    } else {
      return this.vardaApiService.createVarhaiskasvatussuhde(varhaiskasvatussuhdeDTO);
    }
  }

  saveVarhaiskasvatuspaatos(
    isEdit: boolean,
    lapsi: VardaLapsiDTO,
    varhaiskasvatuspaatos: VardaVarhaiskasvatuspaatosDTO,
    data: any): Observable<any> {
    const varhaiskasvatuspaatosFormData = data.formData;
    const varhaiskasvatuspaatosDTO = this.createDTOwithData<VardaVarhaiskasvatuspaatosDTO>(
      varhaiskasvatuspaatosFormData,
      new VardaVarhaiskasvatuspaatosDTO(),
      data.fieldSets);

    varhaiskasvatuspaatosDTO.lapsi = lapsi.url;

    // Replace comma to dot for numeric values before saving
    varhaiskasvatuspaatosDTO.tuntimaara_viikossa = varhaiskasvatuspaatosDTO.tuntimaara_viikossa.replace(',', '.');

    if (isEdit) {
      return this.vardaApiService.editVarhaiskasvatuspaatos(
        this.vardaUtilityService.parseIdFromUrl(varhaiskasvatuspaatos.url), varhaiskasvatuspaatosDTO);
    } else {
      return this.vardaApiService.createVarhaiskasvatuspaatos(varhaiskasvatuspaatosDTO);
    }
  }

  saveKielipainotus(isEdit: boolean, toimipaikka: VardaToimipaikkaDTO, kielipainotus: VardaKielipainotusDTO, data: any): Observable<any> {
    const kielipainotusData = data.kielipainotus;
    const kielipainotusDTO = this.createDTOwithData<VardaKielipainotusDTO>(
      kielipainotusData.formData,
      new VardaKielipainotusDTO(),
      kielipainotusData.fieldSets);
    kielipainotusDTO.toimipaikka = toimipaikka.url;
    if (isEdit) {
      return this.vardaApiService.editKielipainotus(this.vardaUtilityService.parseIdFromUrl(kielipainotus.url), kielipainotusDTO);
    } else {
      return this.vardaApiService.createKielipainotus(kielipainotusDTO);
    }
  }

  saveToimintapainotus(isEdit: boolean, toimipaikka: VardaToimipaikkaDTO,
    toimintapainotus: VardaToimintapainotusDTO, data: any): Observable<any> {
    const toimintapainotusData = data.toimintapainotus;
    const toimintapainotusDTO = this.createDTOwithData<VardaToimintapainotusDTO>(
      toimintapainotusData.formData,
      new VardaToimintapainotusDTO(),
      toimintapainotusData.fieldSets);
    toimintapainotusDTO.toimipaikka = toimipaikka.url;
    if (isEdit) {
      return this.vardaApiService.editToimintapainotus(this.vardaUtilityService.parseIdFromUrl(toimintapainotus.url), toimintapainotusDTO);
    } else {
      return this.vardaApiService.createToimintapainotus(toimintapainotusDTO);
    }
  }

  saveVakatoimijaData(data: any): Observable<any> {
    const vakatoimijaDTO = new VardaVakajarjestaja();
    vakatoimijaDTO.sahkopostiosoite = data.sahkopostiosoite;
    vakatoimijaDTO.puhelinnumero = data.puhelinnumero;
    vakatoimijaDTO.tilinumero = data.tilinumero;
    return this.vardaApiService.patchVakajarjestaja(
      this.vardaVakajarjestajaService.getSelectedVakajarjestajaId(),
      vakatoimijaDTO);
  }

  getHenkilot(): Observable<Array<VardaHenkiloDTO>> {
    return this.vardaApiService.getHenkilot();
  }

  getHenkiloBySsnOrHenkiloOid(ssnOrOid: string, isSsn: boolean): Observable<VardaHenkiloDTO> {
    const henkiloSearchObj = {};
    if (isSsn) {
      henkiloSearchObj['henkilotunnus'] = ssnOrOid;
    } else {
      henkiloSearchObj['henkilo_oid'] = ssnOrOid;
    }
    return this.vardaApiService.getHenkiloBySsnOrHenkiloOid(henkiloSearchObj);
  }

  getToimipaikkaById(toimipaikkaId: string): Observable<VardaToimipaikkaDTO> {
    return this.vardaApiService.getToimipaikkaById(toimipaikkaId);
  }

  getToimipaikatForVakajarjestaja(id: string, searchParams?: any, nextLink?: string): Observable<Array<VardaToimipaikkaDTO>> {
    return this.vardaApiService.getToimipaikatForVakaJarjestaja(id, searchParams, nextLink);
  }

  getLapsetForToimipaikka(id: string, searchParams?: any, nextLink?: string): Observable<VardaPageDto<LapsiByToimipaikkaDTO>> {
    return this.vardaApiService.getLapsetForToimipaikka(
      this.vardaVakajarjestajaService.getSelectedVakajarjestajaId(),
      id,
      searchParams,
      nextLink
    );
  }

  getByPageNo(respData: any, endpoint: string, entityId?: string): any {
    return new Observable((getByPageNoObs) => {
      const paginatedObservables = [];
      let entities = [];
      const noOfResultSets = Math.ceil(respData.count / 20);
      for (let page = 2; page <= noOfResultSets; page++) {
        if (endpoint === VardaEndpoints.getVarhaiskasvatussuhteetByPageNo) {
          paginatedObservables.push(this.vardaApiService.getVarhaiskasvatussuhteetByPageNo(page.toString()));
        } else if (endpoint === VardaEndpoints.getToimipaikatForVakaJarjestajaByPageNo) {
          paginatedObservables.push(this.vardaApiService.getToimipaikatForVakaJarjestajaByPageNo(entityId, page.toString()));
        } else if (endpoint === VardaEndpoints.getVakajarjestajaForLoggedInUserByPageNo) {
          paginatedObservables.push(this.vardaApiService.getVakajarjestajaForLoggedInUserByPageNo(page.toString()));
        } else if (endpoint === VardaEndpoints.getAllVarhaiskasvatussuhteetByToimipaikkaByPageNo) {
          paginatedObservables.push(this.vardaApiService.getAllVarhaiskasvatussuhteetByToimipaikkaByPageNo(entityId, page.toString()));
        } else if (endpoint === VardaEndpoints.getAllMaksutiedotByLapsiByPageNo) {
          paginatedObservables.push(this.vardaApiService.getAllMaksutiedotByLapsiByPageNo(entityId, page));
        } else if (endpoint === VardaEndpoints.getAllLapsetByToimipaikkaByPageNo) {
          paginatedObservables.push(this.vardaApiService.getLapsetForToimipaikka(
            this.vardaVakajarjestajaService.getSelectedVakajarjestajaId(),
            entityId,
            { page },
            null
          ).pipe(map((resp: VardaPageDto<LapsiByToimipaikkaDTO>) => resp.results)));
        }
      }

      forkJoin(paginatedObservables).subscribe((paginatedResults) => {
        paginatedResults.forEach((resultSet) => {
          entities = entities.concat(resultSet);
        });
        getByPageNoObs.next(entities);
      }, (e) => {
        console.error(e);
      });
    });
  }

  getAllByPaginatedResults(allObs: Observable<any>, paginatedEndpointName: string, entityId?: string): Observable<any> {
    let entities = [];
    return new Observable((entitiesObserver) => {
      allObs.subscribe((data) => {
        if (data.next) {
          entities = data.results;
          this.getByPageNo(data, paginatedEndpointName, entityId).subscribe((v) => {
            entities = entities.concat(v);
            entitiesObserver.next(entities);
          });
        } else {
          entitiesObserver.next(data.results);
          entitiesObserver.complete();
        }
      }, (e) => {
        console.error(e);
        entitiesObserver.error();
      });
    });
  }

  getVakajarjestajaForLoggedInUser(): Observable<Array<VardaVakajarjestajaUi>> {
    return this.vardaApiService.getAllVakajarjestajaForLoggedInUser();
  }

  getAllToimipaikatForVakajarjestaja(id: string): Observable<Array<VardaToimipaikkaMinimalDto>> {
    return this.getAllByPaginatedResults(
      this.vardaApiService.getAllToimipaikatForVakaJarjestaja(id),
      VardaEndpoints.getToimipaikatForVakaJarjestajaByPageNo,
      id);
  }

  getLapsiMaksutiedot(lapsiId: any): Observable<Array<VardaMaksutietoDTO>> {
    return this.getAllByPaginatedResults(
      this.vardaApiService.getLapsiMaksupaatokset(lapsiId),
      VardaEndpoints.getAllMaksutiedotByLapsiByPageNo,
      lapsiId);
  }

  getAllLapsetForToimipaikka(toimipaikkaId: string): Observable<Array<LapsiByToimipaikkaDTO>> {
    return this.getAllByPaginatedResults(
      this.vardaApiService.getLapsetForToimipaikka(
        this.vardaVakajarjestajaService.getSelectedVakajarjestajaId(),
        toimipaikkaId,
        null,
        null
      ),
      VardaEndpoints.getAllLapsetByToimipaikkaByPageNo,
      toimipaikkaId
    );
  }

  getKielipainotuksetByToimipaikka(toimipaikkaId: string): Observable<Array<VardaKielipainotusDTO>> {
    return this.vardaApiService.getKielipainotuksetByToimipaikka(toimipaikkaId);
  }

  getToimintapainotuksetByToimipaikka(toimipaikkaId: string): Observable<Array<VardaToimintapainotusDTO>> {
    return this.vardaApiService.getToimintapainotuksetByToimipaikka(toimipaikkaId);
  }

  getVarhaiskasvatussuhteetByLapsi(lapsiId: string): Observable<Array<VardaVarhaiskasvatussuhdeDTO>> {
    return this.vardaApiService.getVarhaiskasvatussuhteetByLapsi(lapsiId);
  }

  getVarhaiskasvatuspaatoksetByLapsi(lapsiId: string): Observable<Array<VardaVarhaiskasvatuspaatosDTO>> {
    return this.vardaApiService.getVarhaiskasvatuspaatoksetByLapsi(lapsiId);
  }

  getYhteenvetoByToimipaikka(toimipaikkaId: string): Observable<VardaToimipaikkaYhteenvetoDTO> {
    return this.vardaApiService.getYhteenveto(toimipaikkaId);
  }

  getCreateLapsiFieldSets(): any {
    return forkJoin([
      this.vardaApiService.getVarhaiskasvatussuhdeFields(),
      this.vardaApiService.getVarhaiskasvatuspaatosFields(),
    ]);
  }

  getMaksutietoFormFieldSets(): Observable<Array<VardaFieldsetArrayContainer>> {
    return forkJoin([
      this.vardaApiService.getMaksutietoFields(),
    ]);
  }

  getHuoltajaFormFieldSets(): Observable<VardaFieldsetArrayContainer> {
    return this.vardaApiService.getHuoltajaFields();
  }

  getToimipaikkaFormFieldSets(): any {
    return forkJoin([
      this.vardaApiService.getToimipaikkaFields(),
      this.vardaApiService.getKielipainotusFields(),
      this.vardaApiService.getToimintapainotusFields()
    ]);
  }

  getVarhaiskasvatuspaatosFieldSets(): any {
    return this.vardaApiService.getVarhaiskasvatuspaatosFields();
  }

  getVakaJarjestajaById(id: string): Observable<VardaVakajarjestaja> {
    return this.vardaApiService.getVakaJarjestajaById(id);
  }

  getPaosJarjestajat(vakajarjestajaId: string, toimipaikkaId: string): Observable<Array<VardaVakajarjestajaUi>> {
    const _apiCallMethod = (page: number) => this.vardaApiService.getPaosJarjestajat(vakajarjestajaId, toimipaikkaId, page);
    return this.vardaApiService.getAllPagesSequentially<VardaVakajarjestajaUi>(_apiCallMethod);
  }

  getEntityReferenceByEndpoint(endpoint: string): Observable<any> {
    let url = endpoint;
    if (environment.production) {
      url = `/varda${endpoint}`;
    }
    return this.http.get(url);
  }

  deleteKielipainotus(kielipainotusId: string): Observable<any> {
    return this.vardaApiService.deleteKielipainotus(kielipainotusId);
  }

  deleteToimintapainotus(toimintapainotusId: string): Observable<any> {
    return this.vardaApiService.deleteToimintapainotus(toimintapainotusId);
  }

  deleteVarhaiskasvatuspaatos(varhaiskasvatuspaatosId: string): Observable<any> {
    return this.vardaApiService.deleteVarhaiskasvatuspaatos(varhaiskasvatuspaatosId);
  }

  deleteVarhaiskasvatussuhde(varhaiskasvatussuhdeId: string): Observable<any> {
    return this.vardaApiService.deleteVarhaiskasvatussuhde(varhaiskasvatussuhdeId);
  }

  deleteLapsi(lapsiId: string): Observable<any> {
    return this.vardaApiService.deleteLapsi(lapsiId);
  }

  createDTOwithData<T>(data: any, dto: T, fieldSets: Array<VardaFieldSet>): T {
    const fieldSetValues = Object.values(data);
    fieldSetValues.forEach((fieldSetItem) => {
      const fieldSetValueKeys = Object.keys(fieldSetItem);
      fieldSetValueKeys.forEach((fieldKey) => {
        dto[fieldKey] = this.getValueForDto(fieldKey, fieldSetItem[fieldKey], fieldSets);

        // Replace comma to dot for numeric values before saving
        if (fieldKey === 'palveluseteli_arvo' || fieldKey === 'asiakasmaksu') {
          dto[fieldKey] = dto[fieldKey].replace(',', '.');
        }
      });
    });
    return dto;
  }

  getValueForDto(key: string, value: any, fieldSets: Array<VardaFieldSet>): any {
    let rv: any = '';
    fieldSets.forEach((fieldset) => {
      fieldset.fields.forEach((field) => {
        if (field.key === key) {
          if (field.widget === VardaWidgetNames.DATE) {
            rv = this.vardaDateService.momentToVardaDate(value);
          } else if (field.widget === VardaWidgetNames.CHECKBOX ||
            field.widget === VardaWidgetNames.BOOLEANRADIO) {
            rv = value ? true : false;
          } else if (field.widget === VardaWidgetNames.AUTOCOMPLETEONE) {
            rv = this.getKoodistoValue(key, value, field);
          } else if (field.widget === VardaWidgetNames.AUTOCOMPLETEONEARR) {
            const v = this.getKoodistoValue(key, value, field);
            rv = [v];
          } else if (field.widget === VardaWidgetNames.SELECTARR) {
            const values = [];
            const valArr = value['selectArr'];
            if (valArr) {
              valArr.forEach((val) => {
                values.push(val);
              });
            }
            rv = values;
          } else if (field.widget === VardaWidgetNames.CHECKBOXGROUP) {
            const values = [];
            if (value) {
              field.options.forEach((option) => {
                if (value[option.code]) {
                  values.push(option.code);
                }
              });
            }
            rv = values;
          } else if (field.widget === VardaWidgetNames.SELECT) {
            rv = value;
          } else {
            rv = value;
          }
        }
      });
    });
    return rv;
  }

  getKoodistoValue(key: string, value: any, field: VardaField): string {
    let rv = '';

    if (!value) {
      return null;
    }

    if (field.koodisto === VardaKoodistot.KIELIKOODISTO) {
      const kieliKoodi = value.koodiArvo;
      rv = kieliKoodi ? kieliKoodi.toUpperCase() : value;
    } else if (field.koodisto === VardaKoodistot.KUNTAKOODISTO) {
      const kuntaKoodi = value.koodiArvo;
      rv = kuntaKoodi ? kuntaKoodi.toUpperCase() : value;
    }

    return rv;
  }

}
