import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { HuoltajaMainModule } from './huoltaja-main/huoltaja-main.module';

import { AppComponent } from './app.component';
import { VardaSharedModule, HttpService } from 'varda-shared';
import { CookieService } from 'ngx-cookie-service';
import { HuoltajaApiService } from './services/huoltaja-api.service';
import { VardaTranslateLoader } from 'varda-shared';


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
  providers: [CookieService],
  bootstrap: [AppComponent],
  exports: []
})
export class AppModule { }
