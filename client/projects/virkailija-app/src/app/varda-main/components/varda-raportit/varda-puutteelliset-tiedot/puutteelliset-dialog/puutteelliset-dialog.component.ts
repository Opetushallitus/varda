import { Component, OnDestroy, OnInit } from '@angular/core';
import { VardaCookieEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/varda-cookie.enum';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-puutteelliset-dialog',
  templateUrl: './puutteelliset-dialog.component.html',
  styleUrls: ['./puutteelliset-dialog.component.css']
})
export class PuutteellisetDialogComponent implements OnDestroy {
  i18n = VirkailijaTranslations;

  ngOnDestroy() {
    sessionStorage.setItem(VardaCookieEnum.puutteelliset_warning, 'seen');
  }
}
