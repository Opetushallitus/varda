import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, Input, NO_ERRORS_SCHEMA, Pipe, PipeTransform } from '@angular/core';
import { VardaMainFrameComponent } from './varda-main-frame.component';
import { VardaModalService } from '../../../core/services/varda-modal.service';
import { VardaApiService } from '../../../core/services/varda-api.service';
import { VardaApiWrapperService } from '../../../core/services/varda-api-wrapper.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';
import { VardaDateService } from '../../services/varda-date.service';
import { vardaApiWrapperServiceStub } from '../../../shared/testmocks/mock-services';
import { toimipaikatStub } from '../../../shared/testmocks/toimipaikat-stub';
import { VardaToimipaikkaDTO } from '../../../utilities/models';
import { VardaKielikoodistoService } from '../../../core/services/varda-kielikoodisto.service';
import { VardaKuntakoodistoService } from '../../../core/services/varda-kuntakoodisto.service';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../../core/auth/auth.service';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';

@Component({ selector: 'app-varda-henkilo-section', template: '' })
class VardaHenkiloSectionComponent {
  @Input() henkilot: any;
}

@Component({ selector: 'app-varda-accessibility-settings', template: '' })
class VardaAccessibilitySettingsComponent { }

@Component({ selector: 'app-varda-modal-form', template: '' })
class VardaModalFormComponent { }

@Component({ selector: 'app-loading-indicator', template: '' })
class VardaLoadingIndicatorComponent { }

@Component({ selector: 'app-varda-toimipaikka-selector', template: '' })
class VardaToimipaikkaSelectorComponent { }

@Pipe({ name: 'translate' })
export class TranslatePipe implements PipeTransform {
  transform() { }
}

describe('VardaMainFrameComponent', () => {
  let component: VardaMainFrameComponent;
  let fixture: ComponentFixture<VardaMainFrameComponent>;

  let authService: AuthService;
  let vardaApiWrapperService: VardaApiWrapperService;
  let vardaVakajarjestajaService: VardaVakajarjestajaService;
  let vardaKieliKoodistoService: VardaKielikoodistoService;
  let vardaKuntaKoodistoService: VardaKuntakoodistoService;

  let setVakajarjestajatSpy;
  let apiWrapperMockFunction;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [
        VardaMainFrameComponent,
        VardaHenkiloSectionComponent,
        VardaAccessibilitySettingsComponent,
        VardaModalFormComponent,
        TranslatePipe
      ],
      schemas: [NO_ERRORS_SCHEMA],
      providers: [
        VardaModalService,
        VardaVakajarjestajaService,
        VardaUtilityService,
        { provide: VardaApiWrapperService, useValue: vardaApiWrapperServiceStub },
        VardaDateService,
        { provide: VardaKielikoodistoService, useValue: { initKielikoodisto: () => { }, sortKielikoodistoOptions: () => { } } },
        { provide: VardaKuntakoodistoService, useValue: { initKuntakoodisto: () => { }, sortKuntakoodistoOptions: () => { } } },
        { provide: VardaApiService, useValue: {} },
        { provide: TranslateService, useValue: {} },
        { provide: AuthService, useValue: { getAuthorizedToimipaikat: () => { }, getUserAccess: () => { } } },
        { provide: Router, useValue: { events: { subscribe: () => { } }, navigate: () => { }, routerState: {} } },
        { provide: HttpClient, useValue: {} },
      ]
    }).compileComponents();

    authService = TestBed.inject<AuthService>(AuthService);
    vardaApiWrapperService = TestBed.inject<VardaApiWrapperService>(VardaApiWrapperService);
    vardaVakajarjestajaService = TestBed.inject<VardaVakajarjestajaService>(VardaVakajarjestajaService);
    const selectedVaka = { id: '111', nimi: 'Nimi' };
    vardaVakajarjestajaService.setVakajarjestajat([selectedVaka]);
    vardaVakajarjestajaService.selectedVakajarjestaja = selectedVaka;
    vardaKieliKoodistoService = TestBed.inject<VardaKielikoodistoService>(VardaKielikoodistoService);
    vardaKuntaKoodistoService = TestBed.inject<VardaKuntakoodistoService>(VardaKuntakoodistoService);

    apiWrapperMockFunction = spyOn(vardaApiWrapperService, 'getAllLapsetForToimipaikka').and.callThrough();
    setVakajarjestajatSpy = spyOn(vardaVakajarjestajaService, 'setVakajarjestajat').and.callThrough();
    vardaVakajarjestajaService.setSelectedToimipaikka(<VardaToimipaikkaMinimalDto>toimipaikatStub[0]);
    vardaVakajarjestajaService.setVakajarjestajaToimipaikat(toimipaikatStub, authService);
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(VardaMainFrameComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('Should set vakajarjestaja and init toimipaikat', () => {
    component.toimipaikat = toimipaikatStub;
    expect(component.toimipaikat.length).toEqual(4);
    component.updateToimipaikatAndVakasuhteet();
    expect(apiWrapperMockFunction).toHaveBeenCalled();
    expect(component.henkilot.length).toEqual(2);
  });

  it('Should fetch varhaiskasvatus- and esiopetussuhteet on toimipaikka change', () => {
    component.toimipaikat = toimipaikatStub;
    component.onToimipaikkaChanged(toimipaikatStub[0]);
    expect(apiWrapperMockFunction).toHaveBeenCalled();
  });
});

