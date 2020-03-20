import { TestBed, inject } from '@angular/core/testing';
import { VardaFormService } from './varda-form.service';
import { VardaApiWrapperService } from './varda-api-wrapper.service';
import { VardaVakajarjestajaService } from './varda-vakajarjestaja.service';
import { VardaDateService } from '../../varda-main/services/varda-date.service';
import { fieldsets } from '../../shared/testmocks/fieldsets';
import { FormGroup } from '@angular/forms';
import { toimipaikatStub } from '../../shared/testmocks/toimipaikat-stub';
import * as moment from 'moment';

describe('VardaFormService', () => {

  let vardaFormService: VardaFormService;

  const varhaiskasvatuspaatoksetFieldSets = fieldsets.varhaiskasvatuspaatokset;
  const toimipaikkaFieldSets = fieldsets.toimipaikat;
  const mockStringField = toimipaikkaFieldSets[0]['fields'][0];
  const mockDateField = toimipaikkaFieldSets[2]['fields'][5];
  const mockSelect1Field = toimipaikkaFieldSets[2]['fields'][0];
  const mockSelect2Field = varhaiskasvatuspaatoksetFieldSets[1]['fields'][0];
  const mockSelectArr1Field = toimipaikkaFieldSets[2]['fields'][2];
  const mockCheckboxField = varhaiskasvatuspaatoksetFieldSets[2]['fields'][2];
  const mockChkgroupField = toimipaikkaFieldSets[2]['fields'][1];
  const mockBooleanRadioField = varhaiskasvatuspaatoksetFieldSets[2]['fields'][1];
  const mockToimipaikanNimiField = toimipaikkaFieldSets[0]['fields'][0];
  const mockToimipaikanToimintamuotoField = toimipaikkaFieldSets[2]['fields'][0];
  const mockToimipaikanKatuosoiteField = toimipaikkaFieldSets[1]['fields'][0];
  const mockVakapaatosHakemusPvm = varhaiskasvatuspaatoksetFieldSets[0]['fields'][0];
  const mockVakapaatosTuntimaara = varhaiskasvatuspaatoksetFieldSets[2]['fields'][0];

  let documentQuerySelectorSpy;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        VardaFormService,
        {provide: VardaApiWrapperService, useValue: {}},
        {provide: VardaVakajarjestajaService, useValue: {}},
        VardaDateService
      ]
    });
    vardaFormService = TestBed.inject<VardaFormService>(VardaFormService);
    documentQuerySelectorSpy = spyOn(document, 'querySelector');
  });

  it('Should return validator functions correctly', () => {
    const validators = vardaFormService.getValidators(mockStringField);
    expect(validators.length).toEqual(4);
  });

  it('Should create formcontrol correctly according to VardaField\'s widget-property', () => {
    const control = vardaFormService.createControl(mockStringField);
    expect(control.value).toEqual('');
    const control3 = vardaFormService.createControl(mockDateField);
    expect(control3.value).toEqual('');
  });

  it('Should create formGroup', () => {
    const fg = vardaFormService.createFieldSetFormGroup();
    expect(fg.controls).not.toBeNull();
    expect(typeof(fg)).toBe('object');
  });

  it('Should set value for string-widget correctly', () => {
    const fc = vardaFormService.createControl(mockStringField);
    vardaFormService.setValue(fc, mockStringField, 'aaa');
    expect(fc.value).toEqual('aaa');
  });

  it('Should set value for date-widget correctly', () => {
    const dateFc = vardaFormService.createControl(mockDateField);
    vardaFormService.setValue(dateFc, mockDateField, '2009-05-04');
    expect(dateFc.value).toEqual(moment('2009-05-04', VardaDateService.vardaApiDateFormat));
  });

  it('Should set value for booleanradio-widget correctly', () => {
    const radioFc1 = vardaFormService.createControl(mockBooleanRadioField);
    vardaFormService.setValue(radioFc1, mockBooleanRadioField, '');
    const radioFc2 = vardaFormService.createControl(mockBooleanRadioField);
    vardaFormService.setValue(radioFc2, mockBooleanRadioField, true);
    const radioFc3 = vardaFormService.createControl(mockBooleanRadioField);
    vardaFormService.setValue(radioFc3, mockBooleanRadioField, false);

    expect(radioFc1.value).toEqual(false);
    expect(radioFc2.value).toEqual(true);
    expect(radioFc3.value).toEqual(false);
  });

  it('Should set value for select-widget correctly', () => {
    const selectFc1 = vardaFormService.createControl(mockSelect1Field);
    const selectFc2 = vardaFormService.createControl(mockSelect2Field);
    vardaFormService.setValue(selectFc1, mockSelect1Field, 'jm02');
    vardaFormService.setValue(selectFc2, mockSelect2Field, 'jm04');
    expect(selectFc1.value).toEqual('jm02');
    expect(selectFc2.value).toEqual('jm04');
  });

  it('Should set value for selectArr-widget correctly', () => {
    const fg1 = <FormGroup> vardaFormService.initFieldSetFormGroup(toimipaikkaFieldSets, toimipaikatStub[0]);
    const selectArrFc1 = fg1.get('3').get('asiointikieli_koodi');
    const fg2 = <FormGroup> vardaFormService.initFieldSetFormGroup(toimipaikkaFieldSets, toimipaikatStub[2]);
    const selectArrFc2 = fg2.get('3').get('asiointikieli_koodi');
    expect(selectArrFc1.value).toEqual({selectArr: ['SE', 'FI', 'HR', 'PT', 'IS']});
    expect(selectArrFc2.value).toEqual({selectArr: [null]});
  });

  it('Should set value for checkbox-widget correctly', () => {
    const checkboxFc1 = vardaFormService.createControl(mockCheckboxField);
    vardaFormService.setValue(checkboxFc1, mockCheckboxField, true);
    const checkboxFc2 = vardaFormService.createControl(mockCheckboxField);
    vardaFormService.setValue(checkboxFc2, mockCheckboxField, '');
    const checkboxFc3 = vardaFormService.createControl(mockCheckboxField);
    vardaFormService.setValue(checkboxFc3, mockCheckboxField, false);
    expect(checkboxFc1.value).toEqual(true);
    expect(checkboxFc2.value).toEqual(false);
    expect(checkboxFc3.value).toEqual(false);
  });

  it('Should set value for chkgroup-widget correctly', () => {
    const chkgroupFc1 = vardaFormService.createControl(mockChkgroupField);
    vardaFormService.setValue(chkgroupFc1, mockChkgroupField, ['jm01', 'jm03', 'jm04']);
    const chkgroupFc2 = vardaFormService.createControl(mockChkgroupField);
    vardaFormService.setValue(chkgroupFc2, mockChkgroupField, ['jm02']);
    expect(chkgroupFc1.value).toEqual({jm01: true, jm02: false, jm03: true, jm04: true});
    expect(chkgroupFc2.value).toEqual({jm01: false, jm02: true, jm03: false, jm04: false});
  });

  it('Should return correct field from fieldsets by fieldkey', () => {
    const paivittainenHoitoField = vardaFormService.findVardaFieldFromFieldSetsByFieldKey('paivittainen_vaka_kytkin',
    varhaiskasvatuspaatoksetFieldSets);
    const paattymisPvmField = vardaFormService.findVardaFieldFromFieldSetsByFieldKey('paattymis_pvm', varhaiskasvatuspaatoksetFieldSets);

    expect(paivittainenHoitoField).not.toBeUndefined();
    expect(paivittainenHoitoField.key).toEqual('paivittainen_vaka_kytkin');

    expect(paattymisPvmField).not.toBeUndefined();
    expect(paattymisPvmField.key).toEqual('paattymis_pvm');
    expect(paattymisPvmField.widget).toEqual('date');
  });

  it('Should return correct form control from form group by fieldkey', () => {

    const fg1 = vardaFormService.initFieldSetFormGroup(varhaiskasvatuspaatoksetFieldSets, null);
    fg1.get('varhaiskasvatuspaatos_varhaiskasvatusaika').patchValue({'paivittainen_vaka_kytkin': true, 'tuntimaara_viikossa': 92});

    const expectedFc1 = vardaFormService.findFormControlFromFormGroupByFieldKey('paivittainen_vaka_kytkin', fg1);
    const expectedFc2 = vardaFormService.findFormControlFromFormGroupByFieldKey('tuntimaara_viikossa', fg1);

    expect(expectedFc1.value).not.toBeUndefined();
    expect(expectedFc1.value).toBeTruthy();

    expect(expectedFc2.value).not.toBeUndefined();
    expect(expectedFc2.value).toEqual(92);
  });

  it('Should disable form control if it has disabledOnEdit-property set', () => {
    const fc1 = vardaFormService.createControl(mockToimipaikanNimiField, null);
    const fc2 = vardaFormService.createControl(mockToimipaikanToimintamuotoField, null, false);
    const fc3 = vardaFormService.createControl(mockToimipaikanNimiField, null, true);
    const fc4 = vardaFormService.createControl(mockToimipaikanToimintamuotoField, null, true);
    const fc7 = vardaFormService.createControl(mockSelect2Field, null, true);

    // Does not have disabledOnEdit-property
    const fc5 = vardaFormService.createControl(mockToimipaikanKatuosoiteField, '', true);
    const fc6 = vardaFormService.createControl(mockSelect2Field, '', false);

    expect(fc1.disabled).toEqual(false);
    expect(fc2.disabled).toEqual(false);
    expect(fc3.disabled).toEqual(true);
    expect(fc4.disabled).toEqual(true);
    expect(fc7.disabled).toEqual(true);
    expect(fc5.disabled).toEqual(false);
    expect(fc6.disabled).toEqual(false);
  });

  it('Should return true or false from isDisabledOnEdit-method depending on disabledOnEdit-rule', () => {
    const jarjestamismuotoIsDisabled = vardaFormService.isDisabledOnEdit(mockSelect2Field, true);
    const hakemusPvmIsDisabled = vardaFormService.isDisabledOnEdit(mockVakapaatosHakemusPvm, true);
    const tuntimaaraViikossaIsDisabled = vardaFormService.isDisabledOnEdit(mockVakapaatosTuntimaara, false);
    expect (jarjestamismuotoIsDisabled).toBeTruthy();
    expect (hakemusPvmIsDisabled).toBeFalsy();
    expect (tuntimaaraViikossaIsDisabled).toBeFalsy();
  });

});
