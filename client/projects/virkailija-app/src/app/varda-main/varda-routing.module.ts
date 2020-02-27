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
import { VardaHakuContainerComponent } from './components/varda-haku-container/varda-haku-container.component';
import { VardaPaosManagementContainerComponent } from './components/varda-paos-management-container/varda-paos-management-container.component';
import { BrowserNotSupportedComponent } from '../shared/components/browser-not-supported/browser-not-supported.component';
import { BrowserNotSupportedGuard } from '../shared/components/browser-not-supported/browser-not-supported.guard';

const routes: Routes = [
  {
    path: '',
    component: VardaDashboardComponent,
    canActivate: [AuthGuard],
    children: [
      {
        path: '',
        component: VardaMainFrameComponent,
        data: { title: 'label.navi.syotto' }
      },
      {
        path: 'vakatoimija',
        component: VardaVakatoimijaComponent,
        data: { title: "label.varhaiskasvatustoimija" }
      },
      {
        path: 'haku',
        component: VardaHakuContainerComponent,
        data: { title: 'label.navi.haku' }
      },
      {
        path: 'tietojen-katselu',
        component: VardaReportingComponent,
        data: { title: 'label.navi.tietojen-katselu' }
      },
      {
        path: 'ohjeet',
        component: VardaInstructionsComponent,
        data: { title: 'label.ohjeet' }
      },
      {
        path: 'ohjeet/:instructionName',
        component: VardaInstructionsComponent,
        data: { title: 'label.ohjeet' }
      },
      {
        path: 'paos-hallinta',
        component: VardaPaosManagementContainerComponent,
        data: { title: 'ohjeet.lisaaminen-ja-muokkaaminen.paos-hallinta' }
      },
    ]
  },
  {
    path: 'login',
    canActivate: [BrowserNotSupportedGuard],
    component: VardaLoginComponent,
    data: { title: 'label.login' }
  },
  {
    path: 'logout',
    component: VardaLogoutComponent,
    data: { title: 'label.logout' }
  },
  {
    path: 'browser-not-supported',
    component: BrowserNotSupportedComponent,
    data: { title: 'Selainta ei tueta / Din webbläsare stöds inte' }
  },
  {
    path: '**',
    component: PageNotFoundComponent,
    data: { title: 'page-not-found.page-not-found' }
  }
];
@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})

export class VardaRoutingModule { }
