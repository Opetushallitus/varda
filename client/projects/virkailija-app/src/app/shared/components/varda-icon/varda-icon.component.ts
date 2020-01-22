import { Component, OnInit, Input } from '@angular/core';

@Component({
  selector: 'app-varda-icon',
  templateUrl: './varda-icon.component.html',
  styleUrls: ['./varda-icon.component.css']
})
export class VardaIconComponent implements OnInit {

  @Input() iconName: string;
  @Input() tooltip: string;
  @Input() size: string;

  iconTooltip: string;

  constructor() { }

  getClasses(): string {
    if (this.size === 'lg') {
      return 'varda-icon-lg';
    }
  }

  ngOnInit() {
    this.iconTooltip = this.tooltip ? this.tooltip : '';
  }

}
