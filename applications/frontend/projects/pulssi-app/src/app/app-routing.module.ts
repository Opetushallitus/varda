import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { PulssiTranslations } from '../assets/i18n/translations.enum';
import { NotFoundComponent } from './components/not-found/not-found.component';
import { PulssiComponent } from './components/pulssi/pulssi.component';


const routes: Routes = [
  {
    path: '',
    component: PulssiComponent,
    data: { title: PulssiTranslations.menu_pulssi }
  },
  {
    path: '**',
    component: NotFoundComponent,
    data: { title: PulssiTranslations.menu_404 }
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
