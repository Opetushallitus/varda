import { TestBed, inject } from '@angular/core/testing';

import { VardaRuleService } from './varda-rule.service';

describe('VardaRuleService', () => {

  let vardaRuleService: VardaRuleService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VardaRuleService]
    });

    vardaRuleService = TestBed.inject<VardaRuleService>(VardaRuleService);
  });

  it('Should return if field has boolean values', () => {
    const ruleFieldsMock1 = {vuorohoito_kytkin: true};
    const formFieldsMock1 = {vuorohoito_kytkin: true};


    const fieldHasBooleanValue1 = vardaRuleService.notAllowedIfKeyHasBooleanValue(ruleFieldsMock1, formFieldsMock1);
    expect(fieldHasBooleanValue1).toBeTruthy();

    const ruleFieldsMock2 = {vuorohoito_kytkin: true};
    const formFieldsMock2 = {vuorohoito_kytkin: false};

    const fieldHasBooleanValue2 = vardaRuleService.notAllowedIfKeyHasBooleanValue(ruleFieldsMock2, formFieldsMock2);
    expect(fieldHasBooleanValue2).toBeFalsy();


    const ruleFieldsMock3 = {vuorohoito_kytkin: false};
    const formFieldsMock3 = {vuorohoito_kytkin: false};

    const fieldHasBooleanValue3 = vardaRuleService.notAllowedIfKeyHasBooleanValue(ruleFieldsMock3, formFieldsMock3);
    expect(fieldHasBooleanValue3).toBeTruthy();
  });

});
