import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { HuoltajaFrontpageComponent } from './components/huoltaja-frontpage/huoltaja-frontpage.component';
import {HuoltajaAuthGuard} from '../huoltaja-auth.guard';
import {HuoltajaUnauthorisedComponent} from '../components/huoltaja-unauthorised/huoltaja-unauthorised.component';

const routes: Routes = [
  {
    path: '',
    canActivate: [HuoltajaAuthGuard],
    component: HuoltajaFrontpageComponent
  },
  {
    path: 'ei-oikeuksia',
    component: HuoltajaUnauthorisedComponent
  }
];
@NgModule({
  imports: [ RouterModule.forChild(routes) ],
  exports: [ RouterModule ]
})

export class HuoltajaRoutingModule {}
