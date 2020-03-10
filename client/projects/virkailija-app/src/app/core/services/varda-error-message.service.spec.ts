import { TestBed, inject } from '@angular/core/testing';

import { VardaErrorMessageService } from './varda-error-message.service';

describe('VardaErrorMessageService', () => {

  let vardaErrorMessageService: VardaErrorMessageService;
  const mockHttpErrorMessageObj = {error: {'kunta_koodi': ['1231231231231 : Not a valid kunta_koodi.'],
  'puhelinnumero': ['+311123123 : Not a valid Finnish phone number.']}};

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VardaErrorMessageService]
    });

    vardaErrorMessageService = TestBed.inject<VardaErrorMessageService>(VardaErrorMessageService);
  });

  it('Should return error message object that has array of errormessages', () => {
    const errorMessageObj = vardaErrorMessageService.getErrorMessages(mockHttpErrorMessageObj);
    expect(errorMessageObj.errorsArr).not.toBeNull();
    expect(errorMessageObj.errorsArr).not.toBeUndefined();
    expect(errorMessageObj.errorsArr.length).toEqual(2);
    expect(errorMessageObj.errorsArr[0].key).toEqual('field.kunta_koodi.label');
  });

  it('Should handle array-type error messages correctly', () => {
    const arrErrorObj = {
      'kayntiosoite_postinumero': [
        '00000 : Postinumero is incorrect.'
      ],
      'hakemus_pvm': [
        'hakemus_pvm must be before alkamis_pvm (or same).'
      ]
    };
    const translatedErrorMsg1 = vardaErrorMessageService.handleArrayErrorMsg(arrErrorObj['kayntiosoite_postinumero']);
    const translatedErrorMsg2 = vardaErrorMessageService.handleArrayErrorMsg(arrErrorObj['hakemus_pvm']);
    expect(translatedErrorMsg1).toEqual('field.postinumero.invalid');
    expect(translatedErrorMsg2).toEqual('field.hakemus_pvm.before_alkamis_pvm');
  });

  it('Should parse and return translation key for dynamic error messages ', () => {
    const arrErrorObj = {
      'varhaiskasvatuspaatos': [
        'Lapsi 20 has already 3 overlapping varhaiskasvatuspaatos on the defined time range.'
      ]
    };
    const translatedErrorMsg = vardaErrorMessageService.handleArrayErrorMsg(arrErrorObj['varhaiskasvatuspaatos']);
    expect(translatedErrorMsg).toEqual('field.lapsi-has-already-three-overlapping-vakapaatos');
  });

  it('Should parse and return translation key for object types', () => {
    const httpErrorObj = {error: {'asiointikieli_koodi': {
      0: [
        'SEPO : Not a valid kieli_koodi.'
      ],
      1: [
        'ASDF : Not a valid kieli_koodi.'
      ]
    }}};
    const errorObj = vardaErrorMessageService.getErrorMessages(httpErrorObj);
    expect(errorObj).not.toBeNull();
    expect(errorObj.errorsArr).not.toBeNull();
    expect(errorObj.errorsArr[0].key).toEqual('field.asiointikieli_koodi.label');
    expect(errorObj.errorsArr[0].msg).toEqual('field.kieli_koodi.invalid');
  });
});
