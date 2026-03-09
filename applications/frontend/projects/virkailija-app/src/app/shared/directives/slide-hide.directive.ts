import { AnimationBuilder, AnimationPlayer, style, animate, AnimationMetadata } from '@angular/animations';
import { Directive, ElementRef, Input } from '@angular/core';

@Directive({
    selector: '[appSlideHide]',
    standalone: false
})

export class SlideHideDirective {
  player: AnimationPlayer;
  private maxHeight = '300px';
  private display: string;

  constructor(private builder: AnimationBuilder, private el: ElementRef) {
    this.display = el.nativeElement.style.display;
    /* If there are perfomance issues due hidden elements possibly try:
      https://stackoverflow.com/questions/43517660/directive-that-works-as-ng-if-angular-2 */
    el.nativeElement.style.display = 'none';
  }

  @Input()
  set appSlideHide(show: boolean) {
    if (this.player) { this.player.destroy(); }

    this.maxHeight = this.el.nativeElement.scrollHeight ? this.el.nativeElement.scrollHeight : '300px';
    const metadata = show ? this.fadeIn() : this.fadeOut();
    const factory = this.builder.build(metadata);
    const player = factory.create(this.el.nativeElement);
    player.play();
  }


  private fadeIn(): AnimationMetadata[] {
    return [
      style({ opacity: 0.5, display: this.display, maxHeight: '100vh' }),
      animate('1s ease-out', style({ opacity: 1, display: 'flex'})),
    ];
  }

  private fadeOut(): AnimationMetadata[] {
    return [
      style({ opacity: '*', maxHeight: this.maxHeight, overflowY: 'hidden' }),
      animate('2s 2s ease-in', style({ opacity: 0.5, maxHeight: '0px', display: 'none' })),
    ];
  }

}
