import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../core/auth/auth.guard';

import {
  VardaDashboardComponent,
  PageNotFoundComponent,
  VardaLoginComponent,
  VardaLogoutComponent,
  VardaReportingComponent,
  VardaMainFrameComponent,
  VardaInstructionsComponent,
  VardaVakatoimijaComponent
} from '../utilities/components';
import {VardaHakuContainerComponent} from './components/varda-haku-container/varda-haku-container.component';
import {VardaPaosManagementContainerComponent} from './components/varda-paos-management-container/varda-paos-management-container.component';

const routes: Routes = [
  {
    path: '',
    component: VardaDashboardComponent,
    canActivate: [AuthGuard],
    children: [
      { path: '', component: VardaMainFrameComponent },
      { path: 'vakatoimija', component: VardaVakatoimijaComponent },
      { path: 'haku', component: VardaHakuContainerComponent },
      { path: 'tietojen-katselu', component: VardaReportingComponent },
      { path: 'ohjeet', component: VardaInstructionsComponent },
      { path: 'ohjeet/:instructionName', component: VardaInstructionsComponent },
      { path: 'paos-hallinta', component: VardaPaosManagementContainerComponent },
    ]},
  { path: 'login', component: VardaLoginComponent},
  { path: 'logout', component: VardaLogoutComponent},
  { path: '**', component: PageNotFoundComponent }
];
@NgModule({
  imports: [ RouterModule.forChild(routes) ],
  exports: [ RouterModule ]
})

export class VardaRoutingModule {}
