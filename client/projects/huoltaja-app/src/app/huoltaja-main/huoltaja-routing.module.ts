import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { HuoltajaFrontpageComponent } from './components/huoltaja-frontpage/huoltaja-frontpage.component';
import { HuoltajaAuthGuard } from '../huoltaja-auth.guard';
import { HuoltajaDashboardComponent } from './components/dashboard/huoltaja-dashboard.component';

const routes: Routes = [
  {
    path: '',
    canActivate: [HuoltajaAuthGuard],
    component: HuoltajaDashboardComponent,
    children: [
      {
        path: '',
        component: HuoltajaFrontpageComponent
      }
    ]
  }
];
@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})

export class HuoltajaRoutingModule { }
