import { TestBed, inject } from '@angular/core/testing';

import { VardaModalService } from './varda-modal.service';

describe('VardaModalService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VardaModalService]
    });
  });

  it('should be created', inject([VardaModalService], (service: VardaModalService) => {
    expect(service).toBeTruthy();
  }));
});
