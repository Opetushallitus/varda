import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { HuoltajaTranslations } from '../../assets/i18n/translations.enum';
import { HuoltajaAuthGuard } from '../huoltaja-auth.guard';
import { HuoltajaDashboardComponent } from './components/dashboard/huoltaja-dashboard.component';
import { LoginFailedComponent } from './components/login/login-failed/login-failed.component';
import { LoginComponent } from './components/login/login.component';
import { EiTietojaComponent } from './components/navigointi/ei-tietoja/ei-tietoja.component';
import { HuoltajuussuhteetComponent } from './components/navigointi/huoltajuussuhteet/huoltajuussuhteet.component';
import { NavigointiComponent } from './components/navigointi/navigointi.component';
import { TyontekijatComponent } from './components/navigointi/tyontekijat/tyontekijat.component';
import { VarhaiskasvatustiedotComponent } from './components/navigointi/varhaiskasvatustiedot/varhaiskasvatustiedot.component';

const routes: Routes = [
  {
    path: '',
    component: HuoltajaDashboardComponent,
    children: [
      {
        path: '',
        component: NavigointiComponent,
        canActivate: [HuoltajaAuthGuard],
        children: [
          {
            path: 'varhaiskasvatustiedot',
            data: { title: HuoltajaTranslations.varhaiskasvatustiedot },
            component: VarhaiskasvatustiedotComponent
          },
          {
            path: 'tyontekijatiedot',
            data: { title: HuoltajaTranslations.tyontekijatiedot },
            component: TyontekijatComponent
          },
          {
            path: 'huoltajuussuhteet',
            data: { title: HuoltajaTranslations.huoltajuussuhteet },
            component: HuoltajuussuhteetComponent
          },
          {
            path: 'ei-tietoja',
            data: { title: HuoltajaTranslations.ei_tietoja },
            component: EiTietojaComponent
          }
        ]
      },
      {
        path: 'login',
        data: { title: 'Kirjaudu sisään / Logga in' },
        component: LoginComponent
      },
      {
        path: 'login-failed',
        data: { title: 'Kirjautuminen epäonnistui / Inloggningen misslyckades' },
        component: LoginFailedComponent
      },
      {
        path: '**',
        redirectTo: ''
      },
    ]
  },

];
@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})

export class HuoltajaRoutingModule { }
