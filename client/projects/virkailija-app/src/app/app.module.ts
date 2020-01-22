import { BrowserModule, Title } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { VardaMainModule } from './varda-main/varda-main.module';
import { HttpModule } from '@angular/http';
import { CoreModule } from './core/core.module';
import { SharedModule } from './shared/shared.module';
import { RouterModule, Routes } from '@angular/router';
import {HttpClientModule, HttpClient, HTTP_INTERCEPTORS } from '@angular/common/http';
import {TranslateModule, TranslateLoader} from '@ngx-translate/core';
import {TranslateHttpLoader} from '@ngx-translate/http-loader';
import { CookieService } from 'ngx-cookie-service';
import { AppComponent } from './app.component';
import { VardaHttpInterceptor } from './core/services/varda-http-interceptor';
import {VardaSharedModule} from 'varda-shared';

// AoT requires an exported function for factories
export function HttpLoaderFactory(http: HttpClient) {
  const path = './assets/i18n/';
  return new TranslateHttpLoader(http, path, '.json');
}

@NgModule({
  declarations: [
    AppComponent
  ],
  imports: [
    BrowserModule,
    HttpModule,
    VardaMainModule,
    CoreModule,
    SharedModule,
    VardaSharedModule,
    RouterModule.forRoot([]),
    HttpClientModule,
    TranslateModule.forRoot({
      loader: {
          provide: TranslateLoader,
          useFactory: (HttpLoaderFactory),
          deps: [HttpClient]
      }
  })
  ],
  providers: [Title, CookieService, { provide: HTTP_INTERCEPTORS, useClass: VardaHttpInterceptor, multi: true }],
  bootstrap: [AppComponent]
})
export class AppModule { }
