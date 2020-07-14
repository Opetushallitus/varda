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
import { HuoltajaFrontpageVakapaatosComponent } from './components/huoltaja-frontpage/huoltaja-vakapaatos/huoltaja-vakapaatos.component';
import { MatDialogModule } from '@angular/material/dialog';
import { ContactDialogComponent} from './components/contact-dialog/contact-dialog.component';
import { VardaSharedModule } from 'varda-shared';


@NgModule({
  imports: [
    CommonModule,
    HuoltajaRoutingModule,
    TranslateModule,
    MatDialogModule,
    MatExpansionModule,
    MatIconModule,
    MatTooltipModule,
    NoopAnimationsModule,
    BrowserAnimationsModule,
    VardaSharedModule
  ],
  declarations: [
    HuoltajaFrontpageComponent,
    HuoltajaFrontpageLapsiComponent,
    HuoltajaFrontpageVakapaatosComponent,
    ContactDialogComponent
  ],
  entryComponents: [ContactDialogComponent],
  exports: [
    HuoltajaFrontpageComponent,
    HuoltajaFrontpageLapsiComponent,
    HuoltajaFrontpageVakapaatosComponent
  ],
  providers: [
  ]
})
export class HuoltajaMainModule { }
