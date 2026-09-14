import { Component, Input } from '@angular/core';
import {VirkailijaTranslations} from "../../../../../assets/i18n/virkailija-translations.enum";

@Component({
    selector: 'app-varda-timestamp',
    templateUrl: './varda-timestamp.component.html',
    styleUrl: './varda-timestamp.component.css',
    standalone: false
})
export class VardaTimestampComponent {
  @Input() dateAdded: string;
  @Input() dateChanged: string;
  i18n = VirkailijaTranslations;

  areDatesWithinSameSecond(date1: string, date2: string): boolean {
    const dateObj1 = new Date(date1);
    const dateObj2 = new Date(date2);
    const differenceInMilliseconds = Math.abs(dateObj1.getTime() - dateObj2.getTime());
    const differenceInSeconds = differenceInMilliseconds / 1000;
    return differenceInSeconds < 1;
  }

}
