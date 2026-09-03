import { Component, Input } from '@angular/core';

@Component({
    selector: 'lib-loading-indicator',
    templateUrl: './loading-indicator.component.html',
    styleUrls: ['./loading-indicator.component.css'],
    standalone: false
})
export class LoadingIndicatorComponent {

  @Input() size: string;
  @Input() isStaticPositioned: boolean;

  constructor() { }
}
