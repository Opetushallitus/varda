import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { VardaRoutingModule } from './varda-routing.module';
import { SharedModule } from '../shared/shared.module';
import { TranslateModule } from '@ngx-translate/core';

import {
  VardaHeaderComponent,
  VardaMainFrameComponent,
  VardaFooterComponent,
  VardaHenkiloItemComponent,
  VardaDashboardComponent,
  VardaLoginComponent,
  VardaLoginFormComponent,
  VardaLogoutComponent,
  VardaLogoutFormComponent,
  VardaToimipaikkaSelectorComponent,
  VardaHenkiloSectionComponent,
  VardaHenkiloListComponent,
  VardaHenkiloFormComponent,
  VardaLapsiFormComponent,
  VardaToimipaikkaFormComponent,
  VardaReportingComponent,
  VardaInstructionsComponent,
  VardaVakatoimijaComponent
} from '../utilities/components';

import { AuthService } from '../core/auth/auth.service';
import { AuthGuard } from '../core/auth/auth.guard';
import { VardaDateService } from './services/varda-date.service';
import { VardaHenkiloService } from './services/varda-henkilo.service';
import { ToimipaikanLapsetComponent } from './components/varda-reporting/toimipaikan-lapset/toimipaikan-lapset.component';
import { ToimipaikanLapsetVakapaatoksetComponent } from './components/varda-reporting/toimipaikan-lapset/toimipaikan-lapset-vakapaatokset/toimipaikan-lapset-vakapaatokset.component';
import { ToimipaikanLapsetVakasuhteetComponent } from './components/varda-reporting/toimipaikan-lapset/toimipaikan-lapset-vakasuhteet/toimipaikan-lapset-vakasuhteet.component';
import { ToimipaikanLapsetMaksutiedotComponent } from './components/varda-reporting/toimipaikan-lapset/toimipaikan-lapset-maksutiedot/toimipaikan-lapset-maksutiedot.component';
import { YhteenvetoComponent } from './components/varda-reporting/yhteenveto/yhteenveto.component';
import { MatTableModule } from '@angular/material';
import { MaksutiedotFormComponent } from './components/varda-lapsi-form/maksutiedot-form/maksutiedot-form.component';
import { HuoltajatContainerComponent } from './components/varda-lapsi-form/huoltajat-container/huoltajat-container.component';
import { VardaHakuContainerComponent } from './components/varda-haku-container/varda-haku-container.component';
import { HakuConditionComponent } from './components/varda-haku-container/haku-condition/haku-condition.component';
import { HakuListComponent } from './components/varda-haku-container/haku-list/haku-list.component';
import { VardaSharedModule } from 'varda-shared';
import { VardaPaosManagementContainerComponent } from './components/varda-paos-management-container/varda-paos-management-container.component';
import { PaosAddedToimijatComponent } from './components/varda-paos-management-container/paos-list-toimintainfo/paos-added-toimijat.component';
import { PaosAddedToimipaikatComponent } from './components/varda-paos-management-container/paos-list-toimintainfo/paos-added-toimipaikat.component';
import { PaosAddPaosToimintaComponent } from './components/varda-paos-management-container/paos-add-paos-toiminta/paos-add-paos-toiminta.component';
import { PaosAddToimintaListComponent } from './components/varda-paos-management-container/paos-add-paos-toiminta/paos-add-toiminta-list/paos-add-toiminta-list.component';
import { MatMenuModule } from '@angular/material/menu';
import { VardaDropdownMenuComponent } from './components/varda-header/varda-dropdown-menu/varda-dropdown-menu.component';

@NgModule({
  imports: [
    CommonModule,
    VardaRoutingModule,
    SharedModule,
    TranslateModule,
    MatTableModule,
    VardaSharedModule,
    MatMenuModule,
  ],
  declarations: [
    VardaHeaderComponent,
    VardaMainFrameComponent,
    VardaFooterComponent,
    VardaToimipaikkaSelectorComponent,
    VardaHenkiloItemComponent,
    VardaDashboardComponent,
    VardaLoginComponent,
    VardaLoginFormComponent,
    VardaLogoutComponent,
    VardaLogoutFormComponent,
    VardaHenkiloSectionComponent,
    VardaHenkiloListComponent,
    VardaLapsiFormComponent,
    VardaHenkiloFormComponent,
    VardaToimipaikkaFormComponent,
    VardaReportingComponent,
    VardaInstructionsComponent,
    VardaVakatoimijaComponent,
    ToimipaikanLapsetComponent,
    ToimipaikanLapsetVakapaatoksetComponent,
    ToimipaikanLapsetVakasuhteetComponent,
    ToimipaikanLapsetMaksutiedotComponent,
    YhteenvetoComponent,
    MaksutiedotFormComponent,
    HuoltajatContainerComponent,
    VardaHakuContainerComponent,
    HakuConditionComponent,
    HakuListComponent,
    VardaPaosManagementContainerComponent,
    PaosAddedToimijatComponent,
    PaosAddedToimipaikatComponent,
    PaosAddPaosToimintaComponent,
    PaosAddToimintaListComponent,
    VardaDropdownMenuComponent,
  ],
  exports: [
    VardaHeaderComponent,
    VardaMainFrameComponent,
    VardaFooterComponent,
    VardaToimipaikkaSelectorComponent,
    VardaHenkiloItemComponent,
    VardaDashboardComponent,
    VardaLoginComponent,
    VardaLoginFormComponent,
    VardaLogoutComponent,
    VardaLogoutFormComponent,
    VardaHenkiloSectionComponent,
    VardaHenkiloListComponent,
    VardaHenkiloFormComponent,
    VardaLapsiFormComponent,
    VardaToimipaikkaFormComponent,
    VardaReportingComponent,
    VardaInstructionsComponent,
    VardaVakatoimijaComponent
  ],
  providers: [
    AuthService,
    AuthGuard,
    VardaDateService,
    VardaHenkiloService
  ]
})
export class VardaMainModule { }
