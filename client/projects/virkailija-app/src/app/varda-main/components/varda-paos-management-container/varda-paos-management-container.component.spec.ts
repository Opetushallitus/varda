import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { Pipe, PipeTransform } from '@angular/core';

import { VardaPaosManagementContainerComponent } from './varda-paos-management-container.component';
import {PaosAddedToimipaikatComponent} from './paos-list-toimintainfo/paos-added-toimipaikat.component';
import {PaosAddedToimijatComponent} from './paos-list-toimintainfo/paos-added-toimijat.component';
import {PaosAddPaosToimintaComponent} from './paos-add-paos-toiminta/paos-add-paos-toiminta.component';
import {VardaVakajarjestajaService} from '../../../core/services/varda-vakajarjestaja.service';
import { ReactiveFormsModule } from '@angular/forms';
import {VardaApiService} from '../../../core/services/varda-api.service';
import { EMPTY } from 'rxjs';
import {PaosAddToimintaListComponent} from './paos-add-paos-toiminta/paos-add-toiminta-list/paos-add-toiminta-list.component';
import {PaosToimintaService} from './paos-toiminta.service';
import {VardaVakajarjestajaUi} from '../../../utilities/models/varda-vakajarjestaja-ui.model';
import {MatFormFieldModule} from '@angular/material/form-field';
import {VardaToggleButtonComponent} from '../../../shared/components/varda-toggle-button/varda-toggle-button.component';
import {VardaDeleteButtonComponent} from '../../../shared/components/varda-delete-button/varda-delete-button.component';
import {VardaErrorAlertComponent} from '../../../shared/components/varda-error-alert/varda-error-alert.component';
import {VardaSharedModule} from 'varda-shared';
import {HttpClient} from '@angular/common/http';
import {VardaPromptModalComponent} from '../../../shared/components/varda-prompt-modal/varda-prompt-modal.component';

@Pipe({name: 'translate'})
export class TranslatePipe implements PipeTransform {
  transform() {}
}

describe('VardaPaosManagementContainerComponent', () => {
  let component: VardaPaosManagementContainerComponent;
  let fixture: ComponentFixture<VardaPaosManagementContainerComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [
        ReactiveFormsModule,
        MatFormFieldModule,
        VardaSharedModule,
      ],
      declarations: [
        VardaPaosManagementContainerComponent,
        PaosAddedToimipaikatComponent,
        PaosAddedToimijatComponent,
        PaosAddPaosToimintaComponent,
        PaosAddToimintaListComponent,
        VardaToggleButtonComponent,
        VardaDeleteButtonComponent,
        VardaErrorAlertComponent,
        VardaPromptModalComponent,
        TranslatePipe,
      ],
      providers: [
        VardaVakajarjestajaService,
        PaosToimintaService,
        {provide: VardaApiService, useValue: {
            getPaosToiminta: () => EMPTY,
            getPaosToimijat: () => EMPTY,
            getAllPagesSequentially: () => EMPTY,
          }
        },
        {provide: HttpClient, useValue: {}},
      ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    const vardaVakajarjestajaService = TestBed.get(VardaVakajarjestajaService);
    vardaVakajarjestajaService.setVakajarjestajat([{id : '111', nimi: 'Nimi'}]);
    vardaVakajarjestajaService.setSelectedVakajarjestaja(new VardaVakajarjestajaUi());
    fixture = TestBed.createComponent(VardaPaosManagementContainerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
