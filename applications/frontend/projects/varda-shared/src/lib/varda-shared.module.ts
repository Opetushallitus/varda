import { NgModule } from '@angular/core';
import { LoadingIndicatorComponent } from './components/loading-indicator/loading-indicator.component';
import { BrowserModule } from '@angular/platform-browser';
import { KoodistoValueDirective } from './directives/koodistoValue.directive';
import { KoodistoPipe } from './directives/koodisto.pipe';
import { LoginTimeoutComponent } from './components/login-timeout/login-timeout.component';
import {VardaDate, VardaDateMinutes, VardaLongDate} from './directives/varda-date.pipe';
import { MarkdownTranslatePipe } from './directives/markdown-translate.pipe';

@NgModule({
  declarations: [
    LoadingIndicatorComponent,
    KoodistoValueDirective,
    KoodistoPipe,
    VardaDate,
    VardaDateMinutes,
    VardaLongDate,
    LoginTimeoutComponent,
    MarkdownTranslatePipe
  ],
  imports: [
    BrowserModule,
  ],
  exports: [
    LoadingIndicatorComponent,
    KoodistoValueDirective,
    KoodistoPipe,
    VardaDate,
    VardaDateMinutes,
    VardaLongDate,
    MarkdownTranslatePipe
  ]
})
export class VardaSharedModule { }
