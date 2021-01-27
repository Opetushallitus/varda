import { Component, Input, OnInit } from '@angular/core';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';

@Component({
  selector: 'app-expansion-panel-title',
  templateUrl: './expansion-panel-title.component.html',
  styleUrls: ['./expansion-panel-title.component.css']
})
export class ExpansionPanelTitleComponent implements OnInit {
  @Input() icon = 'assignment';
  @Input() title: string;
  @Input() secondaryTitle: string;
  @Input() startDate: string;
  @Input() endDate: string;
  @Input() showToggle: string;
  @Input() expanded: boolean;

  i18n = HuoltajaTranslations;
  voimassa: boolean;
  constructor() { }

  ngOnInit(): void {
    this.checkVoimassa();
  }


  checkVoimassa() {
    if (this.startDate) {
      const startDate = this.startDate ? new Date(this.startDate).valueOf() : Date.now();
      const endDate = this.endDate ? new Date(this.endDate) : Date.now();
      const today = Date.now();
      this.voimassa = today >= startDate && today <= endDate;
    }
  }

}
