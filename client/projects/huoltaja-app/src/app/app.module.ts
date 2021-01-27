import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { HuoltajaMainModule } from './huoltaja-main/huoltaja-main.module';
import { AppComponent } from './app.component';
import { VardaSharedModule, HttpService } from 'varda-shared';
import { CookieService } from 'ngx-cookie-service';
import { HuoltajaApiService } from './services/huoltaja-api.service';
import { VardaTranslateLoader } from 'varda-shared';
import { HuoltajaHttpInterceptor } from './services/huoltaja-http.interceptor';

@NgModule({
  declarations: [
    AppComponent
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
        useClass: VardaTranslateLoader,
        deps: [HttpService, HuoltajaApiService]
      }
    })
  ],
  providers: [CookieService, { provide: HTTP_INTERCEPTORS, useClass: HuoltajaHttpInterceptor, multi: true }],
  bootstrap: [AppComponent],
  exports: []
})
export class AppModule { }
