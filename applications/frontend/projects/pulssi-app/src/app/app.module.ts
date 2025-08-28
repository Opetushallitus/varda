import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { AppComponent } from './app.component';
import { HeaderComponent } from './components/header/header.component';
import { PulssiComponent } from './components/pulssi/pulssi.component';
import { registerLocaleData } from '@angular/common';
import localeFi from '@angular/common/locales/fi';
import { HttpClientModule } from '@angular/common/http';
import { HttpService, VardaSharedModule, VardaTranslateLoader } from 'varda-shared';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { NotFoundComponent } from './components/not-found/not-found.component';
import { AppRoutingModule } from './app-routing.module';
import { ApiService } from './services/api.service';
import { FormsModule } from '@angular/forms';

registerLocaleData(localeFi);

@NgModule({
  declarations: [
    AppComponent,
    HeaderComponent,
    PulssiComponent,
    NotFoundComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    VardaSharedModule,
    TranslateModule.forRoot({
      loader: {
        provide: TranslateLoader,
        useClass: VardaTranslateLoader,
        deps: [HttpService, ApiService]
      }
    }),
    FormsModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
