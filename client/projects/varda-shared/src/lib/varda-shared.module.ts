import { NgModule } from '@angular/core';
import { LoadingIndicatorComponent } from './components/loading-indicator/loading-indicator.component';
import { BrowserModule } from '@angular/platform-browser';
import { KoodistoValueDirective } from './directives/koodistoValue.directive';

@NgModule({
  declarations: [LoadingIndicatorComponent, KoodistoValueDirective],
  imports: [
    BrowserModule,
  ],
  exports: [LoadingIndicatorComponent, KoodistoValueDirective]
})
export class VardaSharedModule { }
