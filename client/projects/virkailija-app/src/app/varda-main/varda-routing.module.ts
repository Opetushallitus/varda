import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../core/auth/auth.guard';
import { RoleGuard } from '../core/auth/role.guard';
import {
  VardaDashboardComponent,
  VardaReportingComponent,
  VardaMainFrameComponent,
  VardaVakatoimijaComponent,
  VardaTaydennyskoulutusComponent,
} from '../utilities/components';
import { BrowserNotSupportedComponent, BrowserNotSupportedGuard, LoginFailedComponent, LoginPageComponent, PageNotFoundComponent } from './components/public-components/public-components';
import { VardaPaosManagementContainerComponent } from './components/varda-paos-management-container/varda-paos-management-container.component';
import { VardaHenkilostoTilapainenComponent } from './components/varda-henkilosto-tilapainen/varda-henkilosto-tilapainen.component';
import { VirkailijaTranslations } from '../../assets/i18n/virkailija-translations.enum';
import { VardaSearchToimipaikkaComponent } from './components/varda-reporting/varda-search-toimipaikka/varda-search-toimipaikka.component';
import { VardaSearchTyontekijaComponent } from './components/varda-reporting/varda-search-tyontekija/varda-search-tyontekija.component';
import { VardaYhteenvetoComponent } from './components/varda-reporting/varda-yhteenveto/varda-yhteenveto.component';
import { VardaSearchLapsiComponent } from './components/varda-reporting/varda-search-lapsi/varda-search-lapsi.component';
import { VardaBodyComponent } from './components/varda-body/varda-body.component';
import { UserAccessKeys } from '../utilities/models/varda-user-access.model';

const routes: Routes = [
  {
    path: '',
    component: VardaBodyComponent,
    children: [
      {
        path: '',
        component: VardaDashboardComponent,
        canActivate: [AuthGuard],
        canActivateChild: [RoleGuard],
        children: [
          {
            path: '',
            redirectTo: 'tietojen-katselu',
            pathMatch: 'full'
          },
          {
            path: 'syota-tietoja',
            component: VardaMainFrameComponent,
            data: {
              title: VirkailijaTranslations.navi_syota_tietoja,
              nav_item: 'syota-tietoja',
              roles: [
                UserAccessKeys.lapsitiedot,
                UserAccessKeys.huoltajatiedot,
                UserAccessKeys.tyontekijatiedot,
                UserAccessKeys.taydennyskoulutustiedot
              ]
            }
          },
          {
            path: 'vakatoimija',
            component: VardaVakatoimijaComponent,
            data: { title: VirkailijaTranslations.toimijan_tiedot },
          },
          {
            path: 'tietojen-katselu',
            component: VardaReportingComponent,
            data: { title: VirkailijaTranslations.katsele_tietoja },
            children: [
              {
                path: 'toimipaikat',
                component: VardaSearchToimipaikkaComponent,
                data: {
                  roles: [
                    UserAccessKeys.lapsitiedot,
                    UserAccessKeys.huoltajatiedot,
                    UserAccessKeys.tyontekijatiedot,
                    UserAccessKeys.taydennyskoulutustiedot
                  ]
                }
              },
              {
                path: 'lapset',
                component: VardaSearchLapsiComponent,
                data: {
                  roles: [
                    UserAccessKeys.lapsitiedot,
                    UserAccessKeys.huoltajatiedot,
                  ]
                }
              },
              {
                path: 'tyontekijat',
                component: VardaSearchTyontekijaComponent,
                data: {
                  roles: [
                    UserAccessKeys.tyontekijatiedot,
                    UserAccessKeys.taydennyskoulutustiedot,
                  ]
                }
              },
              {
                path: 'yhteenveto',
                component: VardaYhteenvetoComponent
              },
              {
                path: '',
                pathMatch: 'full',
                redirectTo: 'yhteenveto'
              }
            ]
          },
          {
            path: 'paos-hallinta',
            component: VardaPaosManagementContainerComponent,
            data: {
              title: VirkailijaTranslations.paos,
              nav_item: 'vakatoimija',
              roles: [UserAccessKeys.lapsitiedot]
            }
          },
          {
            path: 'tilapainen-henkilosto',
            component: VardaHenkilostoTilapainenComponent,
            data: {
              title: VirkailijaTranslations.tilapainen_henkilosto,
              roles: [UserAccessKeys.tilapainenHenkilosto]
            },
          },
          {
            path: 'taydennyskoulutus',
            component: VardaTaydennyskoulutusComponent,
            data: {
              title: VirkailijaTranslations.taydennyskoulutukset,
              toimijaRoles: [UserAccessKeys.taydennyskoulutustiedot],
            },

          }
        ]
      },
      {
        path: 'login',
        canActivate: [BrowserNotSupportedGuard],
        component: LoginPageComponent,
        data: { title: 'Kirjaudu sisään / Logga in' }
      },
      {
        path: 'browser-not-supported',
        component: BrowserNotSupportedComponent,
        data: { title: 'Selainta ei tueta / Din webbläsare stöds inte' }
      },
      {
        path: 'login-failed',
        component: LoginFailedComponent,
        data: { title: 'Kirjautuminen epäonnistui / Inloggningen misslyckades' }
      },
      {
        path: '**',
        component: PageNotFoundComponent,
        data: { title: '404 - page not found' }
      }
    ]
  }
];
@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})

export class VardaRoutingModule { }
