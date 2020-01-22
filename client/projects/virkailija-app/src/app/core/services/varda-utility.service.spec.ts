import { TestBed, inject } from '@angular/core/testing';

import { VardaUtilityService } from './varda-utility.service';

describe('VardaUtilityService', () => {

  let vardaUtilityService: VardaUtilityService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VardaUtilityService]
    });

    vardaUtilityService = TestBed.get(VardaUtilityService);
  });

  it('Should parse entity-id from url', () => {
    const id = vardaUtilityService.parseIdFromUrl('https://varda-testing-456.rahtiapp.fi/api/v1/henkilot/3/');
    expect(id).toEqual('3');
  });

});
