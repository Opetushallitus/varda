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
        data: { title: VirkailijaTranslations.navi_syota_tietoja, nav_item: 'syota-tietoja' }
      },
      {
        path: 'vakatoimija',
        component: VardaVakatoimijaComponent,
        data: { title: VirkailijaTranslations.toimijan_tiedot }
      },
      {
        path: 'tietojen-katselu',
        component: VardaReportingComponent,
        data: { title: VirkailijaTranslations.katsele_tietoja }
      },
      {
        path: 'paos-hallinta',
        component: VardaPaosManagementContainerComponent,
        data: { title: VirkailijaTranslations.paos, nav_item: 'vakatoimija' }
      },
      {
        path: 'tilapainen-henkilosto',
        component: VardaHenkilostoTilapainenComponent,
        data: { title: VirkailijaTranslations.tilapainen_henkilosto }
      },
      {
        path: 'taydennyskoulutus',
        component: VardaTaydennyskoulutusComponent,
        data: { title: VirkailijaTranslations.taydennyskoulutukset }
      },
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
