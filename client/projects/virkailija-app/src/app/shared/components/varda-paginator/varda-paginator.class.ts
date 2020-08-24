import { MatPaginatorIntl, PageEvent } from '@angular/material/paginator';
import { TranslateService } from '@ngx-translate/core';
import { Injectable } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

@Injectable()
export class VardaMatPaginator extends MatPaginatorIntl {
  pageOfMax: string;
  i18n = VirkailijaTranslations;
  constructor(
    private translateService: TranslateService,
  ) {
    super();
    this.getTranslations();
  }

  getTranslations() {
    this.translateService.get([
      this.i18n.paginator_page_of_max,
      this.i18n.paginator_items_per_page,
      this.i18n.paginator_first_page,
      this.i18n.paginator_last_page,
      this.i18n.paginator_next_page,
      this.i18n.paginator_previous_page
    ]).subscribe(translation => {
      this.pageOfMax = translation[this.i18n.paginator_page_of_max];
      this.itemsPerPageLabel = translation[this.i18n.paginator_items_per_page];
      this.firstPageLabel = translation[this.i18n.paginator_first_page];
      this.lastPageLabel = translation[this.i18n.paginator_last_page];
      this.nextPageLabel = translation[this.i18n.paginator_next_page];
      this.previousPageLabel = translation[this.i18n.paginator_previous_page];
      this.changes.next();
    });
  }

  getRangeLabel = (page: number, pageSize: number, length: number) => {
    if (length === 0 || pageSize === 0) {
      return null;
    }

    return `${this.pageOfMax} ${page + 1} / ${Math.ceil(length / pageSize)}`;
  }
}
