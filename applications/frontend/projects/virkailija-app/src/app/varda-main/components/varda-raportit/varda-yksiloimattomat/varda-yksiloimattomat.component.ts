import { Component, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { MatTableDataSource } from '@angular/material/table';
import { TranslateService } from '@ngx-translate/core';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaYksiloimatonDTO, YksiloimatonSearchFilter } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-yksiloimaton-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { BehaviorSubject, Observable } from 'rxjs';
import { extractCursor } from "../../../../utilities/helper-functions";


@Component({
    selector: 'app-varda-yksiloimattomat',
    templateUrl: './varda-yksiloimattomat.component.html',
    styleUrls: [
        './varda-yksiloimattomat.component.css',
        '../varda-raportit.component.css'
    ],
    standalone: false
})
export class VardaYksiloimattomatComponent implements OnInit {
  resultCount: number = 0;
  nextCursor: string | null = null;
  prevCursor: string | null = null;
  i18n = VirkailijaTranslations;
  isLoading = new BehaviorSubject<boolean>(true);
  yksiloimattomat: MatTableDataSource<VardaYksiloimatonDTO>;
  yksiloimatonFormErrors: Observable<Array<ErrorTree>>;
  displayedColumns: Array<string>;
  columnFields = [
    { key: 'id', name: 'ID', selected: true },
    { key: 'henkilo_oid', name: 'henkilo_oid', selected: true, disabled: true },
    { key: 'vakatoimija_oid', name: 'vakatoimija_oid', selected: true },
    { key: 'vakatoimija_nimi', name: 'vakatoimija_nimi', selected: true },
  ];

  searchFilter: YksiloimatonSearchFilter = {
    page_size: 500,
    vakatoimija_oid: '',
  };

  private errorService: VardaErrorMessageService;

  constructor(
    private raportitService: VardaRaportitService,
    private translateService: TranslateService,
  ) {
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.yksiloimatonFormErrors = this.errorService.initErrorList();
    this.toggleColumn();
  }


  ngOnInit() {
    this.getYksiloimattomat();
  }

  getYksiloimattomat() {
    this.isLoading.next(true);
    this.yksiloimattomat = null;

    this.raportitService.getYksiloimattomat(this.searchFilter).subscribe({
      next: yksilointiData => {
        this.yksiloimattomat = new MatTableDataSource<VardaYksiloimatonDTO>(yksilointiData.results);
        this.resultCount = yksilointiData.count;
        this.nextCursor = extractCursor(yksilointiData.next);
        this.prevCursor = extractCursor(yksilointiData.previous);
      },
      error: (err) => this.errorService.handleError(err)
    }).add(() => setTimeout(() => this.isLoading.next(false), 1000));
  }

  toggleColumn() {
    this.isLoading.next(true);
    setTimeout(() => {
      const columns = this.columnFields.filter(field => field.selected).map(field => field.key);
      this.displayedColumns = columns;
      if (this.yksiloimattomat) {
        setTimeout(() => this.isLoading.next(false), 1000);
      }
    }, 500);
  }

  searchHenkilot(pageEvent?: PageEvent) {
    if (pageEvent) {
      this.searchFilter.page_size = pageEvent.pageSize;

      const goingForward =
        pageEvent.previousPageIndex !== null &&
        pageEvent.pageIndex > pageEvent.previousPageIndex;

      if (goingForward) {
        if (this.nextCursor) {
          this.searchFilter.cursor = this.nextCursor;
        }
      } else {
        if (this.prevCursor) {
          this.searchFilter.cursor = this.prevCursor;
        }
      }

    } else {
      delete this.searchFilter.cursor;
    }

    this.getYksiloimattomat();
  }
}
