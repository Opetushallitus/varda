import { NgModule } from '@angular/core';
import { LoadingIndicatorComponent } from './components/loading-indicator/loading-indicator.component';
import { BrowserModule } from '@angular/platform-browser';

@NgModule({
  declarations: [LoadingIndicatorComponent],
  imports: [
    BrowserModule,
  ],
  exports: [LoadingIndicatorComponent]
})
export class VardaSharedModule { }
