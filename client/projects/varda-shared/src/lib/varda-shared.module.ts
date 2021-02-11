import { NgModule } from '@angular/core';
import { LoadingIndicatorComponent } from './components/loading-indicator/loading-indicator.component';
import { BrowserModule } from '@angular/platform-browser';
import { KoodistoValueDirective } from './directives/koodistoValue.directive';
import { KoodistoPipe } from './directives/koodisto.pipe';
import { LoginTimeoutComponent } from './components/login-timeout/login-timeout.component';

@NgModule({
  declarations: [LoadingIndicatorComponent, KoodistoValueDirective, KoodistoPipe, LoginTimeoutComponent],
  imports: [
    BrowserModule,
  ],
  exports: [LoadingIndicatorComponent, KoodistoValueDirective, KoodistoPipe]
})
export class VardaSharedModule { }
