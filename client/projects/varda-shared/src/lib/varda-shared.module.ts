import { NgModule } from '@angular/core';
import { LoadingIndicatorComponent } from './components/loading-indicator/loading-indicator.component';
import { BrowserModule } from '@angular/platform-browser';
import { KoodistoValueDirective } from './directives/koodistoValue.directive';
import { KoodistoPipe } from './directives/koodisto.pipe';

@NgModule({
  declarations: [LoadingIndicatorComponent, KoodistoValueDirective, KoodistoPipe],
  imports: [
    BrowserModule,
  ],
  exports: [LoadingIndicatorComponent, KoodistoValueDirective, KoodistoPipe]
})
export class VardaSharedModule { }
