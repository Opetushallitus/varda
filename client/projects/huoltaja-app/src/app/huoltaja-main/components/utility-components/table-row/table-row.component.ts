import { Component, Input } from '@angular/core';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { CodeFormat, KoodistoEnum } from 'varda-shared';


@Component({
  selector: 'app-table-row',
  templateUrl: './table-row.component.html',
  styleUrls: ['./table-row.component.css']
})
export class TableRowComponent {
  @Input() header: string;
  @Input() tooltip: string;
  @Input() content: string;
  @Input() koodisto: KoodistoEnum;
  @Input() format: CodeFormat = 'short';
  i18n = HuoltajaTranslations;

  constructor() { }

}
