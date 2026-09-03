import { Injectable, NgZone, Renderer2, RendererFactory2 } from '@angular/core';
import { Subject, fromEvent } from 'rxjs';
import { filter } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class VardaDomService {
  initInstructionsSubject = new Subject<boolean>();
  private renderer: Renderer2;

  constructor(
    rendererFactory: RendererFactory2,
    private ngZone: NgZone
  ) {
    this.renderer = rendererFactory.createRenderer(null, null);
    this.initializeEventListeners();
  }

  bindTabAndClickEvents(): void {
    this.initializeEventListeners();
  }

  destroyTabAndClickEvents(): void {
    this.initInstructionsSubject.complete();
  }

  private initializeEventListeners(): void {
    // Run outside Angular's change detection to improve performance
    this.ngZone.runOutsideAngular(() => {
      // Listen for tab key events
      fromEvent<KeyboardEvent>(document, 'keydown')
        .pipe(
          filter(event => event.key === 'Tab')
        )
        .subscribe(() => {
          this.handleTabbing();
        });

      // Listen for mouse events
      fromEvent(document, 'mousedown')
        .subscribe(() => {
          this.handleClicking();
        });
    });
  }

  private handleTabbing(): void {
    this.ngZone.run(() => {
      this.renderer.removeClass(document.body, 'user-is-clicking');
      this.renderer.addClass(document.body, 'user-is-tabbing');
    });
  }

  private handleClicking(): void {
    this.ngZone.run(() => {
      this.renderer.removeClass(document.body, 'user-is-tabbing');
      this.renderer.addClass(document.body, 'user-is-clicking');
    });
  }
}
