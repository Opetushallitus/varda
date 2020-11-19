import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { VardaRoutingModule } from './varda-routing.module';
import { SharedModule } from '../shared/shared.module';
import { TranslateModule } from '@ngx-translate/core';

import {
  VardaHeaderComponent,
  VardaMainFrameComponent,
  VardaFooterComponent,
  VardaDashboardComponent,
  VardaToimipaikkaSelectorComponent,
  VardaLapsiSectionComponent,
  VardaHenkiloListComponent,
  VardaHenkiloFormComponent,
  VardaLapsiFormComponent,
  VardaToimipaikkaFormComponent,
  VardaReportingComponent,
  VardaVakatoimijaComponent,
  VardaHenkilostoSectionComponent,
  VardaTyontekijaFormComponent,
  VardaActionRowComponent,
  VardaErrorFieldComponent,
  VardaTyontekijaTutkintoComponent,
  VardaTyontekijaTaydennyskoulutusComponent,
  VardaPalvelussuhdeComponent,
  VardaTyoskentelypaikkaComponent,
  VardaPalvelussuhteetComponent,
  VardaPoissaoloComponent,
  VardaTaydennyskoulutusComponent,
  VardaTaydennyskoulutusFormComponent,
  VardaTaydennyskoulutusOsallistujaListComponent,
  VardaTaydennyskoulutusOsallistujaPickerComponent,
  VardaTyontekijaTaydennyskoulutuksetComponent,
  VardaDeleteHenkiloComponent,
  VardaVarhaiskasvatuspaatosComponent,
  VardaVarhaiskasvatuspaatoksetComponent,
  VardaVarhaiskasvatussuhdeComponent,
  VardaMaksutietoComponent,
  VardaMaksutietoHuoltajaComponent,
  VardaMaksutiedotComponent,
} from '../utilities/components';

import { AuthService } from '../core/auth/auth.service';
import { AuthGuard } from '../core/auth/auth.guard';
import { RoleGuard } from '../core/auth/role.guard';
import { VardaDateService } from './services/varda-date.service';
import { VardaHenkiloService } from './services/varda-henkilo.service';
import { MatTableModule } from '@angular/material/table';
import { VardaSharedModule } from 'varda-shared';
import { VardaPaosManagementContainerComponent } from './components/varda-paos-management-container/varda-paos-management-container.component';
import { PaosAddedToimijatComponent } from './components/varda-paos-management-container/paos-list-toimintainfo/paos-added-toimijat.component';
import { PaosAddedToimipaikatComponent } from './components/varda-paos-management-container/paos-list-toimintainfo/paos-added-toimipaikat.component';
import { PaosAddPaosToimintaComponent } from './components/varda-paos-management-container/paos-add-paos-toiminta/paos-add-paos-toiminta.component';
import { PaosAddToimintaListComponent } from './components/varda-paos-management-container/paos-add-paos-toiminta/paos-add-toiminta-list/paos-add-toiminta-list.component';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { VardaHenkilostoTilapainenComponent } from './components/varda-henkilosto-tilapainen/varda-henkilosto-tilapainen.component';
import { EiHenkilostoaDialogComponent } from './components/varda-henkilosto-tilapainen/ei-henkilostoa-dialog/ei-henkilostoa-dialog.component';
import { MatDialogModule } from '@angular/material/dialog';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { VardaSearchLapsiComponent } from './components/varda-reporting/varda-search-lapsi/varda-search-lapsi.component';
import { VardaSearchToimipaikkaComponent } from './components/varda-reporting/varda-search-toimipaikka/varda-search-toimipaikka.component';
import { VardaSearchTyontekijaComponent } from './components/varda-reporting/varda-search-tyontekija/varda-search-tyontekija.component';
import { VardaYhteenvetoComponent } from './components/varda-reporting/varda-yhteenveto/varda-yhteenveto.component';
import { VardaResultListComponent } from './components/varda-reporting/varda-result-list/varda-result-list.component';
import { VardaResultInfoComponent } from './components/varda-reporting/varda-result-info/varda-result-info.component';
import { VardaResultToimipaikkaComponent } from './components/varda-reporting/varda-result-toimipaikka/varda-result-toimipaikka.component';
import { VardaResultTyontekijaComponent } from './components/varda-reporting/varda-result-tyontekija/varda-result-tyontekija.component';
import { VardaResultLapsiComponent } from './components/varda-reporting/varda-result-lapsi/varda-result-lapsi.component';
import { VardaBodyComponent } from './components/varda-body/varda-body.component';
import { BrowserNotSupportedComponent, BrowserNotSupportedGuard, LoginFailedComponent, LoginPageComponent, PageNotFoundComponent } from './components/public-components/public-components';

@NgModule({
  imports: [
    CommonModule,
    VardaRoutingModule,
    SharedModule,
    TranslateModule,
    MatTableModule,
    MatTooltipModule,
    VardaSharedModule,
    MatMenuModule,
    MatDialogModule,
    MatProgressBarModule,
    MatProgressSpinnerModule
  ],
  declarations: [
    VardaHeaderComponent,
    VardaHenkilostoTilapainenComponent,
    VardaMainFrameComponent,
    VardaFooterComponent,
    VardaToimipaikkaSelectorComponent,
    VardaDashboardComponent,
    VardaLapsiSectionComponent,
    VardaHenkilostoSectionComponent,
    VardaHenkiloListComponent,
    VardaLapsiFormComponent,
    VardaTyontekijaFormComponent,
    VardaActionRowComponent,
    VardaDeleteHenkiloComponent,
    VardaErrorFieldComponent,
    VardaTyontekijaTutkintoComponent,
    VardaTyontekijaTaydennyskoulutuksetComponent,
    VardaTyontekijaTaydennyskoulutusComponent,
    VardaTaydennyskoulutusComponent,
    VardaTaydennyskoulutusFormComponent,
    VardaTaydennyskoulutusOsallistujaListComponent,
    VardaTaydennyskoulutusOsallistujaPickerComponent,
    VardaPalvelussuhteetComponent,
    VardaPalvelussuhdeComponent,
    VardaTyoskentelypaikkaComponent,
    VardaPoissaoloComponent,
    VardaHenkiloFormComponent,
    VardaToimipaikkaFormComponent,
    VardaVarhaiskasvatuspaatosComponent,
    VardaVarhaiskasvatuspaatoksetComponent,
    VardaVarhaiskasvatussuhdeComponent,
    VardaReportingComponent,
    VardaVakatoimijaComponent,
    VardaYhteenvetoComponent,
    VardaMaksutietoComponent,
    VardaMaksutietoHuoltajaComponent,
    VardaMaksutiedotComponent,
    VardaPaosManagementContainerComponent,
    PaosAddedToimijatComponent,
    PaosAddedToimipaikatComponent,
    PaosAddPaosToimintaComponent,
    PaosAddToimintaListComponent,
    EiHenkilostoaDialogComponent,
    VardaSearchToimipaikkaComponent,
    VardaSearchLapsiComponent,
    VardaSearchToimipaikkaComponent,
    VardaSearchTyontekijaComponent,
    VardaResultListComponent,
    VardaResultInfoComponent,
    VardaResultToimipaikkaComponent,
    VardaResultTyontekijaComponent,
    VardaResultLapsiComponent,
    VardaBodyComponent,
    LoginPageComponent,
    LoginFailedComponent,
    PageNotFoundComponent,
    BrowserNotSupportedComponent
  ],
  entryComponents: [EiHenkilostoaDialogComponent],
  exports: [
    VardaHeaderComponent,
    VardaHenkilostoTilapainenComponent,
    VardaMainFrameComponent,
    VardaFooterComponent,
    VardaToimipaikkaSelectorComponent,
    VardaDashboardComponent,
    VardaLapsiSectionComponent,
    VardaHenkilostoSectionComponent,
    VardaHenkiloListComponent,
    VardaHenkiloFormComponent,
    VardaLapsiFormComponent,
    VardaTyontekijaFormComponent,
    VardaActionRowComponent,
    VardaDeleteHenkiloComponent,
    VardaErrorFieldComponent,
    VardaTyontekijaTutkintoComponent,
    VardaTyontekijaTaydennyskoulutuksetComponent,
    VardaTyontekijaTaydennyskoulutusComponent,
    VardaTaydennyskoulutusComponent,
    VardaTaydennyskoulutusFormComponent,
    VardaTaydennyskoulutusOsallistujaListComponent,
    VardaTaydennyskoulutusOsallistujaPickerComponent,
    VardaPalvelussuhteetComponent,
    VardaPalvelussuhdeComponent,
    VardaVarhaiskasvatussuhdeComponent,
    VardaTyoskentelypaikkaComponent,
    VardaPoissaoloComponent,
    VardaToimipaikkaFormComponent,
    VardaReportingComponent,
    VardaVakatoimijaComponent
  ],
  providers: [
    AuthService,
    AuthGuard,
    RoleGuard,
    BrowserNotSupportedGuard,
    VardaDateService,
    VardaHenkiloService
  ]
})
export class VardaMainModule { }
