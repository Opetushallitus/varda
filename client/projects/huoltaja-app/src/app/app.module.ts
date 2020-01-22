import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { HttpClientModule, HttpClient } from '@angular/common/http';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { TranslateHttpLoader } from '@ngx-translate/http-loader';
import { HuoltajaMainModule } from './huoltaja-main/huoltaja-main.module';

import { AppComponent } from './app.component';
import { VardaSharedModule } from 'varda-shared';
import { CookieService } from 'ngx-cookie-service';
import { HuoltajaUnauthorisedComponent } from './components/huoltaja-unauthorised/huoltaja-unauthorised.component';

// AoT requires an exported function for factories
export function HttpLoaderFactory(http: HttpClient) {
  const path = './assets/i18n/';
  return new TranslateHttpLoader(http, path, '.json');
}

@NgModule({
  declarations: [
    AppComponent,
    HuoltajaUnauthorisedComponent
  ],
  imports: [
    BrowserModule,
    HuoltajaMainModule,
    RouterModule.forRoot([]),
    VardaSharedModule,
    HttpClientModule,
    TranslateModule.forRoot({
      loader: {
          provide: TranslateLoader,
          useFactory: (HttpLoaderFactory),
          deps: [HttpClient]
      }
    })
  ],
  providers: [CookieService],
  bootstrap: [AppComponent]
})
export class AppModule { }
