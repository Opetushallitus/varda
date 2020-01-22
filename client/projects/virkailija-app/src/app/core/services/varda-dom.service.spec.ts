import { TestBed, inject } from '@angular/core/testing';

import { VardaDomService } from './varda-dom.service';

describe('VardaDomService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VardaDomService]
    });
  });

  it('should be created', inject([VardaDomService], (service: VardaDomService) => {
    expect(service).toBeTruthy();
  }));
});
