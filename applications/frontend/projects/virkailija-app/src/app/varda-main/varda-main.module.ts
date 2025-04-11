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
import { MatTableModule } from '@angular/material/table';
import { VardaSharedModule } from 'varda-shared';
import { VardaPaosManagementContainerComponent } from './components/varda-paos-management-container/varda-paos-management-container.component';
import { PaosAddedToimijatComponent } from './components/varda-paos-management-container/paos-list-toimintainfo/paos-added-toimijat.component';
import { PaosAddedToimipaikatComponent } from './components/varda-paos-management-container/paos-list-toimintainfo/paos-added-toimipaikat.component';
import { PaosAddPaosToimintaComponent } from './components/varda-paos-management-container/paos-add-paos-toiminta/paos-add-paos-toiminta.component';
import { PaosAddToimintaListComponent } from './components/varda-paos-management-container/paos-add-paos-toiminta/paos-add-toiminta-list/paos-add-toiminta-list.component';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { VardaHenkilostoVuokrattuComponent } from './components/varda-henkilosto-vuokrattu/varda-henkilosto-vuokrattu.component';
import { EiHenkilostoaDialogComponent } from './components/varda-henkilosto-vuokrattu/ei-henkilostoa-dialog/ei-henkilostoa-dialog.component';
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
import { VardaRaportitComponent } from './components/varda-raportit/varda-raportit.component';
import { VardaYksiloimattomatComponent } from './components/varda-raportit/varda-yksiloimattomat/varda-yksiloimattomat.component';
import { VardaPuutteellisetTiedotComponent } from './components/varda-raportit/varda-puutteelliset-tiedot/varda-puutteelliset-tiedot.component';
import { VardaPuutteellisetTyontekijatComponent } from './components/varda-raportit/varda-puutteelliset-tiedot/puutteelliset-tyontekijat/puutteelliset-tyontekijat.component';
import { VardaPuutteellisetLapsetComponent } from './components/varda-raportit/varda-puutteelliset-tiedot/puutteelliset-lapset/puutteelliset-lapset.component';
import { VardaTiedonsiirrotComponent } from './components/varda-raportit/varda-tiedonsiirrot/varda-tiedonsiirrot.component';
import { VardaTiedonsiirtoComponent } from './components/varda-raportit/varda-tiedonsiirrot/tiedonsiirto/tiedonsiirto.component';
import { VardaTiedonsiirrotYhteenvetoComponent } from './components/varda-raportit/varda-tiedonsiirrot/tiedonsiirrot-yhteenveto/tiedonsiirrot-yhteenveto.component';
import { TiedonsiirtoDialogComponent } from './components/varda-raportit/varda-tiedonsiirrot/tiedonsiirto-dialog/tiedonsiirto-dialog.component';
import { PuutteellisetDialogComponent } from './components/varda-raportit/varda-puutteelliset-tiedot/puutteelliset-dialog/puutteelliset-dialog.component';
import { VardaFormErrorIconComponent } from './components/varda-form-error-icon/varda-form-error-icon.component';
import { VardaFormErrorListComponent } from './components/varda-form-error-list/varda-form-error-list.component';
import { TiedonsiirtoFilterHeaderComponent } from './components/varda-raportit/varda-tiedonsiirrot/tiedonsiirto-filter-header/tiedonsiirto-filter-header.component';
import { TiedonsiirtoFilterComponent } from './components/varda-raportit/varda-tiedonsiirrot/tiedonsiirto-filter/tiedonsiirto-filter.component';
import { PuutteellisetListComponent } from './components/varda-raportit/varda-puutteelliset-tiedot/puutteelliset-list/puutteelliset-list.component';
import { ToimipaikkaPainotuksetComponent } from './components/varda-toimipaikka-form/toimipaikka-painotukset/toimipaikka-painotukset.component';
import { KielipainotusComponent } from './components/varda-toimipaikka-form/toimipaikka-painotukset/kielipainotus/kielipainotus.component';
import { ToimintapainotusComponent } from './components/varda-toimipaikka-form/toimipaikka-painotukset/toimintapainotus/toimintapainotus.component';
import { VardaExcelComponent } from './components/varda-raportit/varda-excel/varda-excel.component';
import { VardaExcelNewComponent } from './components/varda-raportit/varda-excel/varda-excel-new/varda-excel-new.component';
import { VardaPuutteellisetToimipaikatComponent } from './components/varda-raportit/varda-puutteelliset-tiedot/puutteelliset-toimipaikat/puutteelliset-toimipaikat.component';
import { VardaTransferOutageComponent } from './components/varda-raportit/varda-transfer-outage/varda-transfer-outage.component';
import { VardaRequestSummaryComponent } from './components/varda-raportit/varda-request-summary/varda-request-summary.component';
import { VardaSetPaattymisPvmComponent } from './components/varda-set-paattymis-pvm/varda-set-paattymis-pvm.component';
import { MatTableDummyComponent } from '../shared/components/mat-table-dummy/mat-table-dummy.component';
import { VardaTyontekijaExtraComponent } from './components/varda-henkilo-form/varda-tyontekija-form/varda-tyontekija-extra/varda-tyontekija-extra.component';
import {
  VardaPuutteellisetOrganisaatioComponent
} from './components/varda-raportit/varda-puutteelliset-tiedot/puutteelliset-organisaatio/puutteelliset-organisaatio.component';
import { VardaTukipaatosComponent } from './components/varda-tukipaatos/varda-tukipaatos/varda-tukipaatos.component';
import {
  VardaReminderReportComponent
} from "./components/varda-raportit/varda-reminder-report/varda-reminder-report/varda-reminder-report.component";
import {
    VardaTimestampComponent
} from "./components/varda-henkilo-form/varda-timestamp/varda-timestamp.component";

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
    VardaHenkilostoVuokrattuComponent,
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
    BrowserNotSupportedComponent,
    VardaRaportitComponent,
    VardaYksiloimattomatComponent,
    VardaPuutteellisetTiedotComponent,
    VardaPuutteellisetTyontekijatComponent,
    VardaPuutteellisetLapsetComponent,
    VardaPuutteellisetToimipaikatComponent,
    VardaPuutteellisetOrganisaatioComponent,
    VardaTiedonsiirrotComponent,
    VardaTiedonsiirtoComponent,
    VardaTiedonsiirrotYhteenvetoComponent,
    TiedonsiirtoDialogComponent,
    PuutteellisetDialogComponent,
    VardaFormErrorIconComponent,
    VardaFormErrorListComponent,
    TiedonsiirtoFilterHeaderComponent,
    TiedonsiirtoFilterComponent,
    PuutteellisetListComponent,
    ToimipaikkaPainotuksetComponent,
    KielipainotusComponent,
    ToimintapainotusComponent,
    VardaExcelComponent,
    VardaExcelNewComponent,
    VardaTransferOutageComponent,
    VardaRequestSummaryComponent,
    VardaSetPaattymisPvmComponent,
    MatTableDummyComponent,
    VardaTyontekijaExtraComponent,
    VardaTukipaatosComponent,
    VardaReminderReportComponent,
    VardaTimestampComponent,
  ],
  exports: [
    VardaHeaderComponent,
    VardaHenkilostoVuokrattuComponent,
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
    BrowserNotSupportedGuard
  ]
})
export class VardaMainModule { }
