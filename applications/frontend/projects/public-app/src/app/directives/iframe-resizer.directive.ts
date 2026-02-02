// https://github.com/davidjbradshaw/iframe-resizer/issues/478#issuecomment-347958630
import {AfterViewInit, Directive, ElementRef, OnDestroy} from '@angular/core';
import iframeResizer, {IFrameComponent} from '@iframe-resizer/core';

@Directive({
    selector: '[appIframeResizer]',
    standalone: false
})
export class IFrameResizerDirective implements AfterViewInit, OnDestroy {
  component: IFrameComponent;

  constructor(public element: ElementRef) {
  }

  ngAfterViewInit() {
    const components = iframeResizer({
      checkOrigin: false,
      heightCalculationMethod: 'documentElementOffset',
      log: false
    }, this.element.nativeElement);

    /* save component reference so we can close it later */
    this.component = components && components.length > 0 ? components[0] : null;
  }

  ngOnDestroy(): void {
    if (this.component && this.component.iFrameResizer) {
      this.component.iFrameResizer.close();
    }
  }
}
