import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { HuoltajaFrontpageComponent } from './components/huoltaja-frontpage/huoltaja-frontpage.component';
import {HuoltajaAuthGuard} from '../huoltaja-auth.guard';

const routes: Routes = [
  {
    path: '',
    canActivate: [HuoltajaAuthGuard],
    component: HuoltajaFrontpageComponent
  }
];
@NgModule({
  imports: [ RouterModule.forChild(routes) ],
  exports: [ RouterModule ]
})

export class HuoltajaRoutingModule {}
