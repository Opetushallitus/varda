import { TestBed, inject } from '@angular/core/testing';

import { VardaValidatorService } from './varda-validator.service';
import { VardaRuleService } from './varda-rule.service';
import { VardaFormService } from './varda-form.service';
import { VardaDateService } from '../../varda-main/services/varda-date.service';
import { VardaVakajarjestajaService } from './varda-vakajarjestaja.service';
import { fieldsets } from '../../shared/testmocks/fieldsets';

describe('VardaValidatorService', () => {

  let vardaValidatorService: VardaValidatorService;
  let vardaFormService: VardaFormService;

  const varhaiskasvatuspaatoksetFieldSets = fieldsets.varhaiskasvatuspaatokset;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VardaValidatorService, VardaRuleService, VardaFormService, VardaDateService, VardaVakajarjestajaService]
    });

    vardaValidatorService = TestBed.get(VardaValidatorService);
    vardaFormService = TestBed.get(VardaFormService);
  });

  it('Should run validators if field has dependent fields', () => {
    const fg1 = vardaFormService.initFieldSetFormGroup(varhaiskasvatuspaatoksetFieldSets, null);
    const vuoroHoitoKytkinField = vardaFormService.findVardaFieldFromFieldSetsByFieldKey('vuorohoito_kytkin',
    varhaiskasvatuspaatoksetFieldSets);
    const vuoroHoitoKytkinFieldFc = vardaFormService.findFormControlFromFormGroupByFieldKey('vuorohoito_kytkin', fg1);

    const paivittainenHoitoKytkinField = vardaFormService.findVardaFieldFromFieldSetsByFieldKey('vuorohoito_kytkin',
    varhaiskasvatuspaatoksetFieldSets);

    expect(paivittainenHoitoKytkinField.hidden).toBeFalsy();

    vuoroHoitoKytkinFieldFc.setValue(true);
    vuoroHoitoKytkinFieldFc.updateValueAndValidity();

    vardaValidatorService.validate(vuoroHoitoKytkinField, varhaiskasvatuspaatoksetFieldSets, fg1);

    const paivittainenHoitoKytkinFieldFc = vardaFormService.findVardaFieldFromFieldSetsByFieldKey('paivittainen_vaka_kytkin',
    varhaiskasvatuspaatoksetFieldSets);

    expect(paivittainenHoitoKytkinFieldFc.hidden).toBeTruthy();
  });
});
