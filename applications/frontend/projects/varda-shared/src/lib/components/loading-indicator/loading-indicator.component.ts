import { Component, Input } from '@angular/core';

@Component({
  selector: 'lib-loading-indicator',
  templateUrl: './loading-indicator.component.html',
  styleUrls: ['./loading-indicator.component.css']
})
export class LoadingIndicatorComponent {

  @Input() size: string;
  @Input() isStaticPositioned: boolean;

  constructor() { }
}
