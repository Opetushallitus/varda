import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../core/auth/auth.guard';
import { RoleGuard } from '../core/auth/role.guard';
import {
  VardaDashboardComponent,
  VardaMainFrameComponent,
  VardaReportingComponent,
  VardaTaydennyskoulutusComponent,
  VardaVakatoimijaComponent,
} from '../utilities/components';
import {
  BrowserNotSupportedComponent,
  BrowserNotSupportedGuard,
  LoginFailedComponent,
  LoginPageComponent,
  PageNotFoundComponent
} from './components/public-components/public-components';
import { VardaPaosManagementContainerComponent } from './components/varda-paos-management-container/varda-paos-management-container.component';
import { VardaHenkilostoTilapainenComponent } from './components/varda-henkilosto-tilapainen/varda-henkilosto-tilapainen.component';
import { VirkailijaTranslations } from '../../assets/i18n/virkailija-translations.enum';
import { VardaSearchToimipaikkaComponent } from './components/varda-reporting/varda-search-toimipaikka/varda-search-toimipaikka.component';
import { VardaSearchTyontekijaComponent } from './components/varda-reporting/varda-search-tyontekija/varda-search-tyontekija.component';
import { VardaYhteenvetoComponent } from './components/varda-reporting/varda-yhteenveto/varda-yhteenveto.component';
import { VardaSearchLapsiComponent } from './components/varda-reporting/varda-search-lapsi/varda-search-lapsi.component';
import { VardaBodyComponent } from './components/varda-body/varda-body.component';
import { UserAccessKeys } from '../utilities/models/varda-user-access.model';
import { VardaRaportitComponent } from './components/varda-raportit/varda-raportit.component';
import { VardaPuutteellisetTiedotComponent } from './components/varda-raportit/varda-puutteelliset-tiedot/varda-puutteelliset-tiedot.component';
import { VardaTiedonsiirtoComponent } from './components/varda-raportit/varda-tiedonsiirrot/tiedonsiirto/tiedonsiirto.component';
import { VardaTiedonsiirrotYhteenvetoComponent } from './components/varda-raportit/varda-tiedonsiirrot/tiedonsiirrot-yhteenveto/tiedonsiirrot-yhteenveto.component';
import { VardaTiedonsiirrotComponent } from './components/varda-raportit/varda-tiedonsiirrot/varda-tiedonsiirrot.component';
import { VardaYksiloimattomatComponent } from './components/varda-raportit/varda-yksiloimattomat/varda-yksiloimattomat.component';
import { VardaExcelComponent } from './components/varda-raportit/varda-excel/varda-excel.component';
import { VardaExcelNewComponent } from './components/varda-raportit/varda-excel/varda-excel-new/varda-excel-new.component';
import { VardaTransferOutageComponent } from './components/varda-raportit/varda-transfer-outage/varda-transfer-outage.component';
import { VardaPuutteellisetToimipaikatComponent } from './components/varda-raportit/varda-puutteelliset-tiedot/puutteelliset-toimipaikat/puutteelliset-toimipaikat.component';
import { VardaPuutteellisetLapsetComponent } from './components/varda-raportit/varda-puutteelliset-tiedot/puutteelliset-lapset/puutteelliset-lapset.component';
import { VardaPuutteellisetTyontekijatComponent } from './components/varda-raportit/varda-puutteelliset-tiedot/puutteelliset-tyontekijat/puutteelliset-tyontekijat.component';
import { VardaRequestSummaryComponent } from './components/varda-raportit/varda-request-summary/varda-request-summary.component';
import { VardaYearlyReportComponent } from './components/varda-raportit/varda-yearly-report/varda-yearly-report.component';
import { VardaSetPaattymisPvmComponent } from './components/varda-set-paattymis-pvm/varda-set-paattymis-pvm.component';

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
              ],
              requireTallentaja: true
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
                  title: VirkailijaTranslations.katsele_tietoja_toimipaikat,
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
                  title: VirkailijaTranslations.katsele_tietoja_lapset,
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
                  title: VirkailijaTranslations.katsele_tietoja_tyontekijat,
                  roles: [
                    UserAccessKeys.tyontekijatiedot,
                    UserAccessKeys.taydennyskoulutustiedot,
                  ]
                }
              },
              {
                path: 'yhteenveto',
                component: VardaYhteenvetoComponent,
                data: {
                  title: VirkailijaTranslations.katsele_tietoja_yhteenveto
                }
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

          },
          {
            path: 'raportit',
            component: VardaRaportitComponent,
            data: { title: VirkailijaTranslations.raportit },
            children: [
              {
                path: 'puutteelliset-tiedot',
                component: VardaPuutteellisetTiedotComponent,
                data: {
                  title: VirkailijaTranslations.puutteelliset_tiedot,
                  toimijaRoles: [
                    UserAccessKeys.raportit,
                    UserAccessKeys.lapsitiedot,
                    UserAccessKeys.tyontekijatiedot,
                    UserAccessKeys.huoltajatiedot
                  ]
                },
                children: [
                  {
                    path: 'toimipaikat',
                    component: VardaPuutteellisetToimipaikatComponent,
                    data: {
                      title: VirkailijaTranslations.toimipaikka_plural,
                      toimijaRoles: [
                        UserAccessKeys.raportit,
                        UserAccessKeys.lapsitiedot,
                        UserAccessKeys.tyontekijatiedot
                      ]
                    }
                  },
                  {
                    path: 'lapset',
                    component: VardaPuutteellisetLapsetComponent,
                    data: {
                      title: VirkailijaTranslations.henkilo_lapset,
                      toimijaRoles: [
                        UserAccessKeys.raportit,
                        UserAccessKeys.lapsitiedot,
                        UserAccessKeys.huoltajatiedot
                      ]
                    }
                  },
                  {
                    path: 'tyontekijat',
                    component: VardaPuutteellisetTyontekijatComponent,
                    data: {
                      title: VirkailijaTranslations.henkilo_tyontekijat,
                      toimijaRoles: [UserAccessKeys.raportit, UserAccessKeys.tyontekijatiedot]
                    }
                  }
                ]
              },
              {
                path: 'yksiloimattomat',
                component: VardaYksiloimattomatComponent,
                data: {
                  title: VirkailijaTranslations.yksiloimattomat_title,
                  toimijaRoles: [
                    UserAccessKeys.oph
                  ]
                }
              },
              {
                path: 'transfer-outage',
                component: VardaTransferOutageComponent,
                data: {
                  title: VirkailijaTranslations.transfer_outage,
                  toimijaRoles: [
                    UserAccessKeys.oph
                  ]
                },
                children: [
                  {
                    path: 'palvelukayttaja',
                    component: VardaTransferOutageComponent,
                    data: { title: VirkailijaTranslations.transfer_outage_service_user }
                  },
                  {
                    path: 'organisaatio',
                    component: VardaTransferOutageComponent,
                    data: { title: VirkailijaTranslations.vakajarjestaja }
                  },
                  {
                    path: 'lahdejarjestelma',
                    component: VardaTransferOutageComponent,
                    data: { title: VirkailijaTranslations.lahdejarjestelma }
                  },
                  {
                    path: '',
                    pathMatch: 'full',
                    redirectTo: 'palvelukayttaja'
                  },
                ]
              },
              {
                path: 'request-summary',
                component: VardaRequestSummaryComponent,
                data: {
                  title: VirkailijaTranslations.request_summary,
                  toimijaRoles: [
                    UserAccessKeys.oph
                  ]
                }
              },
              {
                path: 'tiedonsiirrot',
                component: VardaTiedonsiirrotComponent,
                data: {
                  title: VirkailijaTranslations.tiedonsiirrot,
                  toimijaRoles: [UserAccessKeys.raportit, UserAccessKeys.oph],
                },
                children: [
                  {
                    path: 'yhteenveto',
                    component: VardaTiedonsiirrotYhteenvetoComponent,
                    data: { title: VirkailijaTranslations.tiedonsiirrot_yhteenveto }
                  },
                  {
                    path: 'onnistuneet',
                    component: VardaTiedonsiirtoComponent,
                    data: { title: VirkailijaTranslations.tiedonsiirrot_onnistuneet }
                  },
                  {
                    path: 'epaonnistuneet',
                    component: VardaTiedonsiirtoComponent,
                    data: { title: VirkailijaTranslations.tiedonsiirrot_epaonnistuneet }
                  },
                  {
                    path: '',
                    pathMatch: 'full',
                    redirectTo: 'yhteenveto'
                  }
                ]
              },
              {
                path: 'excel/new',
                component: VardaExcelNewComponent,
                data: {
                  title: VirkailijaTranslations.excel_new,
                  toimijaRoles: [UserAccessKeys.raportit, UserAccessKeys.oph]
                }
              },
              {
                path: 'excel',
                component: VardaExcelComponent,
                data: {
                  title: VirkailijaTranslations.excel,
                  toimijaRoles: [UserAccessKeys.raportit, UserAccessKeys.oph]
                }
              },
              {
                path: 'vuosiraportti',
                component: VardaYearlyReportComponent,
                data: {
                  title: VirkailijaTranslations.yearly_report,
                  toimijaRoles: [UserAccessKeys.raportit, UserAccessKeys.oph]
                }
              },
              {
                path: '',
                pathMatch: 'full',
                redirectTo: 'puutteelliset-tiedot'
              }
            ]
          },
          {
            path: 'paata-tiedot',
            component: VardaSetPaattymisPvmComponent,
            data: {
              title: VirkailijaTranslations.paata_tiedot,
              roles: [UserAccessKeys.oph]
            }
          },
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
