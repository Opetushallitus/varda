import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { PublicKoodistotComponent } from './components/public-koodistot/public-koodistot.component';
import { PublicKoodistotDetailComponent } from './components/public-koodistot/public-koodistot-detail/public-koodistot-detail.component';
import { PublicSwaggerComponent } from './components/public-swagger/public-swagger.component';
import { PublicDataModelComponent } from './components/public-model-visualization/public-data-model.component';
import { PublicTranslations } from '../assets/i18n/translations.enum';
import { PublicNotFoundComponent } from './components/public-not-found/public-not-found.component';


const routes: Routes = [
  {
    path: 'koodistot',
    component: PublicKoodistotComponent,
    data: { title: PublicTranslations.menu_koodistot },
    children: [
      {
        path: ':koodisto',
        component: PublicKoodistotDetailComponent
      }
    ]
  },
  {
    path: 'swagger',
    component: PublicSwaggerComponent,
    data: { title: PublicTranslations.menu_swagger }
  },
  {
    path: 'tietomalli',
    component: PublicDataModelComponent,
    data: { title: PublicTranslations.menu_data_model }
  },
  {
    path: '',
    redirectTo: '/koodistot',
    pathMatch: 'full'
  },
  {
    path: '**',
    component: PublicNotFoundComponent,
    data: { title: PublicTranslations.menu_404 }
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
