import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { PublicHeaderComponent } from './components/public-header/public-header.component';
import { PublicKoodistotComponent } from './components/public-koodistot/public-koodistot.component';
import { PublicKoodistotDetailComponent } from './components/public-koodistot/public-koodistot-detail/public-koodistot-detail.component';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { TranslateHttpLoader } from '@ngx-translate/http-loader';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { MatIconModule } from '@angular/material/icon';
import { VardaSharedModule } from 'varda-shared';
import { FormsModule } from '@angular/forms';

// AoT requires an exported function for factories
export function HttpLoaderFactory(http: HttpClient) {
  const path = './assets/i18n/';
  return new TranslateHttpLoader(http, path, '.json');
}

@NgModule({
  declarations: [
    AppComponent,
    PublicHeaderComponent,
    PublicKoodistotComponent,
    PublicKoodistotDetailComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    VardaSharedModule,
    TranslateModule.forRoot({
      loader: {
        provide: TranslateLoader,
        useFactory: (HttpLoaderFactory),
        deps: [HttpClient]
      }
    }),
    MatIconModule,
    FormsModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
