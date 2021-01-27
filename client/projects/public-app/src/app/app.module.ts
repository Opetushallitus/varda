import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { PublicHeaderComponent } from './components/public-header/public-header.component';
import { PublicKoodistotComponent } from './components/public-koodistot/public-koodistot.component';
import { PublicKoodistotDetailComponent } from './components/public-koodistot/public-koodistot-detail/public-koodistot-detail.component';
import { HttpClientModule } from '@angular/common/http';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { MatIconModule } from '@angular/material/icon';
import { HttpService, VardaSharedModule, VardaTranslateLoader } from 'varda-shared';
import { FormsModule } from '@angular/forms';
import { PublicIframeComponent } from './components/public-iframe/public-iframe.component';
import { IFrameResizerDirective } from './directives/iframe-resizer.directive';
import { PublicSwaggerComponent } from './components/public-swagger/public-swagger.component';
import { PublicDataModelComponent } from './components/public-model-visualization/public-data-model.component';
import { PublicApiService } from './services/public-api.service';
import { PublicNotFoundComponent } from './components/public-not-found/public-not-found.component';

@NgModule({
  declarations: [
    AppComponent,
    PublicHeaderComponent,
    PublicKoodistotComponent,
    PublicKoodistotDetailComponent,
    PublicIframeComponent,
    PublicSwaggerComponent,
    PublicDataModelComponent,
    PublicNotFoundComponent,
    IFrameResizerDirective
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
        deps: [HttpService, PublicApiService]
      }
    }),
    MatIconModule,
    FormsModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
