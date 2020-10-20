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
  VardaLoginComponent,
  VardaLoginFormComponent,
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
  TyontekijaFormActionRowComponent,
  VardaTyontekijaErrorComponent,
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
  VardaDeleteHenkiloComponent,
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
import { MatTableModule } from '@angular/material/table';
import { MaksutiedotFormComponent } from './components/varda-lapsi-form/maksutiedot-form/maksutiedot-form.component';
import { HuoltajatContainerComponent } from './components/varda-lapsi-form/huoltajat-container/huoltajat-container.component';
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
import { VardaTyontekijaTaydennyskoulutuksetComponent } from './components/varda-tyontekija-form/varda-tyontekija-taydennyskoulutukset/varda-tyontekija-taydennyskoulutukset.component';
import { ReportTyontekijaComponent } from './components/varda-reporting/report-tyontekija/report-tyontekija.component';

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
    VardaLoginComponent,
    VardaLoginFormComponent,
    VardaLapsiSectionComponent,
    VardaHenkilostoSectionComponent,
    VardaHenkiloListComponent,
    VardaLapsiFormComponent,
    VardaTyontekijaFormComponent,
    TyontekijaFormActionRowComponent,
    VardaDeleteHenkiloComponent,
    VardaTyontekijaErrorComponent,
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
    VardaReportingComponent,
    VardaVakatoimijaComponent,
    ToimipaikanLapsetComponent,
    ToimipaikanLapsetVakapaatoksetComponent,
    ToimipaikanLapsetVakasuhteetComponent,
    ToimipaikanLapsetMaksutiedotComponent,
    YhteenvetoComponent,
    MaksutiedotFormComponent,
    HuoltajatContainerComponent,
    VardaPaosManagementContainerComponent,
    PaosAddedToimijatComponent,
    PaosAddedToimipaikatComponent,
    PaosAddPaosToimintaComponent,
    PaosAddToimintaListComponent,
    EiHenkilostoaDialogComponent,
    ReportTyontekijaComponent
  ],
  entryComponents: [EiHenkilostoaDialogComponent],
  exports: [
    VardaHeaderComponent,
    VardaHenkilostoTilapainenComponent,
    VardaMainFrameComponent,
    VardaFooterComponent,
    VardaToimipaikkaSelectorComponent,
    VardaDashboardComponent,
    VardaLoginComponent,
    VardaLoginFormComponent,
    VardaLapsiSectionComponent,
    VardaHenkilostoSectionComponent,
    VardaHenkiloListComponent,
    VardaHenkiloFormComponent,
    VardaLapsiFormComponent,
    VardaTyontekijaFormComponent,
    TyontekijaFormActionRowComponent,
    VardaDeleteHenkiloComponent,
    VardaTyontekijaErrorComponent,
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
    VardaToimipaikkaFormComponent,
    VardaReportingComponent,
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
