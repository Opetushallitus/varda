import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HuoltajaRoutingModule } from './huoltaja-routing.module';
import { TranslateModule } from '@ngx-translate/core';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NoopAnimationsModule, BrowserAnimationsModule } from '@angular/platform-browser/animations';

import { HuoltajaFrontpageComponent } from './components/huoltaja-frontpage/huoltaja-frontpage.component';
import { HuoltajaFrontpageLapsiComponent } from './components/huoltaja-frontpage/huoltaja-frontpage-lapsi/huoltaja-frontpage-lapsi.component';
import { HuoltajaFrontpageVakasuhdeComponent } from './components/huoltaja-frontpage/huoltaja-frontpage-vakasuhde/huoltaja-frontpage-vakasuhde.component';

@NgModule({
  imports: [
    CommonModule,
    HuoltajaRoutingModule,
    TranslateModule,
    MatExpansionModule,
    MatIconModule,
    MatTooltipModule,
    NoopAnimationsModule,
    BrowserAnimationsModule
  ],
  declarations: [
    HuoltajaFrontpageComponent,
    HuoltajaFrontpageLapsiComponent,
    HuoltajaFrontpageVakasuhdeComponent
  ],
  exports: [
    HuoltajaFrontpageComponent,
    HuoltajaFrontpageLapsiComponent,
    HuoltajaFrontpageVakasuhdeComponent
  ],
  providers: [
  ]
})
export class HuoltajaMainModule { }
