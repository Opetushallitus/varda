import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../core/auth/auth.guard';

import {
  VardaDashboardComponent,
  PageNotFoundComponent,
  VardaLoginComponent,
  VardaReportingComponent,
  VardaMainFrameComponent,
  VardaVakatoimijaComponent,
  VardaTaydennyskoulutusComponent
} from '../utilities/components';
import { VardaHakuContainerComponent } from './components/varda-haku-container/varda-haku-container.component';
import { VardaPaosManagementContainerComponent } from './components/varda-paos-management-container/varda-paos-management-container.component';
import { BrowserNotSupportedComponent } from '../shared/components/browser-not-supported/browser-not-supported.component';
import { BrowserNotSupportedGuard } from '../shared/components/browser-not-supported/browser-not-supported.guard';
import { VardaHenkilostoTilapainenComponent } from './components/varda-henkilosto-tilapainen/varda-henkilosto-tilapainen.component';
import { VirkailijaTranslations } from '../../assets/i18n/virkailija-translations.enum';

const routes: Routes = [
  {
    path: '',
    component: VardaDashboardComponent,
    canActivate: [AuthGuard],
    children: [
      {
        path: '',
        component: VardaMainFrameComponent,
        data: { title: 'label.navi.syotto', nav_item: 'syota-tietoja' }
      },
      {
        path: 'vakatoimija',
        component: VardaVakatoimijaComponent,
        data: { title: 'label.varhaiskasvatustoimija' }
      },
      {
        path: 'tietojen-katselu',
        component: VardaReportingComponent,
        data: { title: 'label.navi.tietojen-katselu' }
      },
      {
        path: 'paos-hallinta',
        component: VardaPaosManagementContainerComponent,
        data: { title: VirkailijaTranslations.paos_title, nav_item: 'vakatoimija' }
      },
      {
        path: 'tilapainen-henkilosto',
        component: VardaHenkilostoTilapainenComponent,
        data: { title: VirkailijaTranslations.tilapainen_henkilosto }
      },
      /* {
        path: 'taydennyskoulutus',
        component: VardaTaydennyskoulutusComponent,
        data: { title: VirkailijaTranslations.taydennyskoulutukset }
      }, */
    ]
  },
  {
    path: 'login',
    canActivate: [BrowserNotSupportedGuard],
    component: VardaLoginComponent,
    data: { title: 'Kirjaudu sisään / Logga in' }
  },
  {
    path: 'browser-not-supported',
    component: BrowserNotSupportedComponent,
    data: { title: 'Selainta ei tueta / Din webbläsare stöds inte' }
  },
  {
    path: '**',
    component: PageNotFoundComponent,
    data: { title: '404 - page not found' }
  }
];
@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})

export class VardaRoutingModule { }
