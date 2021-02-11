import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HuoltajaRoutingModule } from './huoltaja-routing.module';
import { TranslateModule } from '@ngx-translate/core';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatListModule } from '@angular/material/list';
import { NoopAnimationsModule, BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HuoltajaDashboardComponent } from './components/dashboard/huoltaja-dashboard.component';
import { MatDialogModule } from '@angular/material/dialog';
import { ContactDialogComponent } from './components/utility-components/contact-dialog/contact-dialog.component';
import { VardaSharedModule } from 'varda-shared';
import { NavigointiComponent } from './components/navigointi/navigointi.component';
import { HenkilotiedotComponent } from './components/navigointi/henkilotiedot/henkilotiedot.component';
import { TyontekijatComponent } from './components/navigointi/tyontekijat/tyontekijat.component';
import { HuoltajuussuhteetComponent } from './components/navigointi/huoltajuussuhteet/huoltajuussuhteet.component';
import { MatTabsModule } from '@angular/material/tabs';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MaksutietoComponent } from './components/navigointi/huoltajuussuhteet/huoltajuussuhde/maksutieto/maksutieto.component';
import { TableRowComponent } from './components/utility-components/table-row/table-row.component';
import { LoginComponent } from './components/login/login.component';
import { FormsModule } from '@angular/forms';
import { VarhaiskasvatustiedotComponent } from './components/navigointi/varhaiskasvatustiedot/varhaiskasvatustiedot.component';
import { VarhaiskasvatuspaatosComponent } from './components/navigointi/varhaiskasvatustiedot/varhaiskasvatuspaatos/varhaiskasvatuspaatos.component';
import { TyontekijaComponent } from './components/navigointi/tyontekijat/tyontekija/tyontekija.component';
import { TutkinnotComponent } from './components/navigointi/tyontekijat/tyontekija/tutkinnot/tutkinnot.component';
import { PalvelussuhdeComponent } from './components/navigointi/tyontekijat/tyontekija/palvelussuhde/palvelussuhde.component';
import { TyoskentelypaikkaComponent } from './components/navigointi/tyontekijat/tyontekija/palvelussuhde/tyoskentelypaikka/tyoskentelypaikka.component';
import { ExpansionPanelTitleComponent } from './components/utility-components/expansion-panel-title/expansion-panel-title.component';
import { HuoltajaDatePipe, HuoltajaMonthPipe } from './components/pipes/date.pipe';
import { TaydennyskoulutusComponent } from './components/navigointi/tyontekijat/tyontekija/taydennyskoulutus/taydennyskoulutus.component';
import { HuoltajuussuhdeComponent } from './components/navigointi/huoltajuussuhteet/huoltajuussuhde/huoltajuussuhde.component';
import { LoginFailedComponent } from './components/login/login-failed/login-failed.component';
import { VarhaiskasvatustiedotContactDialogComponent } from './components/utility-components/contact-dialog/varhaiskasvatustiedot-contact-dialog/varhaiskasvatustiedot-contact-dialog.component';
import { HuoltajuussuhteetContactDialogComponent } from './components/utility-components/contact-dialog/huoltajuussuhteet-contact-dialog/huoltajuussuhteet-contact-dialog.component';
import { TyontekijatiedotContactDialogComponent } from './components/utility-components/contact-dialog/tyontekijatiedot-contact-dialog/tyontekijatiedot-contact-dialog.component';
import { EiTietojaComponent } from './components/navigointi/ei-tietoja/ei-tietoja.component';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    HuoltajaRoutingModule,
    TranslateModule,
    MatDialogModule,
    MatExpansionModule,
    MatIconModule,
    MatTabsModule,
    MatSelectModule,
    MatTooltipModule,
    NoopAnimationsModule,
    BrowserAnimationsModule,
    VardaSharedModule,
    MatListModule,
    MatSnackBarModule
  ],
  declarations: [
    HuoltajaDashboardComponent,
    ContactDialogComponent,
    NavigointiComponent,
    HenkilotiedotComponent,
    TyontekijatComponent,
    HuoltajuussuhteetComponent,
    MaksutietoComponent,
    LoginComponent,
    VarhaiskasvatustiedotComponent,
    VarhaiskasvatuspaatosComponent,
    TyontekijaComponent,
    TutkinnotComponent,
    PalvelussuhdeComponent,
    TyoskentelypaikkaComponent,
    ExpansionPanelTitleComponent,
    HuoltajaDatePipe,
    HuoltajaMonthPipe,
    TaydennyskoulutusComponent,
    HuoltajuussuhdeComponent,
    LoginFailedComponent,
    VarhaiskasvatustiedotContactDialogComponent,
    HuoltajuussuhteetContactDialogComponent,
    TyontekijatiedotContactDialogComponent,
    EiTietojaComponent,
    TableRowComponent
  ],
  entryComponents: [ContactDialogComponent],
  exports: [
    HuoltajaDashboardComponent,
    HenkilotiedotComponent
  ],
  providers: [
  ]
})
export class HuoltajaMainModule { }
