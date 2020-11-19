import { Injectable } from '@angular/core';
import { Observable, forkJoin } from 'rxjs';
import { FormGroup } from '@angular/forms';
import { VardaApiService } from './varda-api.service';
import { VardaVakajarjestajaService } from './varda-vakajarjestaja.service';
import { VardaUtilityService } from './varda-utility.service';
import { VardaDateService } from '../../varda-main/services/varda-date.service';

import {
  VardaFieldSet,
  VardaWidgetNames,
  VardaToimipaikkaDTO,
  VardaKielipainotusDTO,
  VardaToimintapainotusDTO,
  VardaField,
} from '../../utilities/models';
import { KoodistoEnum, LoadingHttpService } from 'varda-shared';

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

  saveToimipaikka(isEdit: boolean, toimipaikka: VardaToimipaikkaDTO, data: any): Observable<any> {
    const toimipaikkaData = data.toimipaikka;
    const toimipaikkaDTO = this.createDTOwithData<VardaToimipaikkaDTO>(
      toimipaikkaData.formData,
      new VardaToimipaikkaDTO(),
      toimipaikkaData.fieldSets);
    toimipaikkaDTO.vakajarjestaja = VardaApiService.getVakajarjestajaUrlFromId(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().id);
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

  getKielipainotuksetByToimipaikka(toimipaikkaId: string): Observable<Array<VardaKielipainotusDTO>> {
    return this.vardaApiService.getKielipainotuksetByToimipaikka(toimipaikkaId);
  }

  getToimintapainotuksetByToimipaikka(toimipaikkaId: string): Observable<Array<VardaToimintapainotusDTO>> {
    return this.vardaApiService.getToimintapainotuksetByToimipaikka(toimipaikkaId);
  }

  getToimipaikkaFormFieldSets(): any {
    return forkJoin([
      this.vardaApiService.getToimipaikkaFields(),
      this.vardaApiService.getKielipainotusFields(),
      this.vardaApiService.getToimintapainotusFields()
    ]);
  }

  deleteKielipainotus(kielipainotusId: string): Observable<any> {
    return this.vardaApiService.deleteKielipainotus(kielipainotusId);
  }

  deleteToimintapainotus(toimintapainotusId: string): Observable<any> {
    return this.vardaApiService.deleteToimintapainotus(toimintapainotusId);
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

    if (field.koodisto === KoodistoEnum.kieli) {
      const kieliKoodi = value.koodiArvo;
      rv = kieliKoodi ? kieliKoodi.toUpperCase() : value;
    } else if (field.koodisto === KoodistoEnum.kunta) {
      const kuntaKoodi = value.koodiArvo;
      rv = kuntaKoodi ? kuntaKoodi.toUpperCase() : value;
    }

    return rv;
  }

}
