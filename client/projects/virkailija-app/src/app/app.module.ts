import { BrowserModule, Title } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { VardaMainModule } from './varda-main/varda-main.module';
import { CoreModule } from './core/core.module';
import { SharedModule } from './shared/shared.module';
import { RouterModule } from '@angular/router';
import { HttpClientModule, HttpClient, HTTP_INTERCEPTORS } from '@angular/common/http';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { TranslateHttpLoader } from '@ngx-translate/http-loader';
import { CookieService } from 'ngx-cookie-service';
import { AppComponent } from './app.component';
import { VardaSharedModule, HttpService, VardaHttpInterceptor, VardaTranslateLoader } from 'varda-shared';
import { VardaApiService } from './core/services/varda-api.service';
import { registerLocaleData } from '@angular/common';
import localeFi from '@angular/common/locales/fi';

// AoT requires an exported function for factories
export const HttpLoaderFactory = (http: HttpClient) => {
  const path = './assets/i18n/';
  return new TranslateHttpLoader(http, path, '.json');
};

registerLocaleData(localeFi);

@NgModule({
  declarations: [
    AppComponent
  ],
  imports: [
    BrowserModule,
    VardaMainModule,
    CoreModule,
    SharedModule,
    VardaSharedModule,
    RouterModule.forRoot([]),
    HttpClientModule,
    TranslateModule.forRoot({
      loader: {
        provide: TranslateLoader,
        useClass: VardaTranslateLoader,
        deps: [HttpService, VardaApiService]
      }
    })
  ],
  providers: [Title, CookieService, { provide: HTTP_INTERCEPTORS, useClass: VardaHttpInterceptor, multi: true }],
  bootstrap: [AppComponent]
})
export class AppModule { }
