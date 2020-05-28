import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { PublicKoodistotComponent } from './components/public-koodistot/public-koodistot.component';
import { PublicKoodistotDetailComponent } from './components/public-koodistot/public-koodistot-detail/public-koodistot-detail.component';


const routes: Routes = [
  {
    path: 'koodistot',
    component: PublicKoodistotComponent,
    data: { title: 'title.koodistot' },
    children: [
      {
        path: ':koodisto',
        component: PublicKoodistotDetailComponent
      }
    ]
  },
  {
    path: '',
    redirectTo: '/koodistot',
    pathMatch: 'full'
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
