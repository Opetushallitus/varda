import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { SearchResult } from '../varda-search-abstract.component';
import { Observable } from 'rxjs';
import { delay } from 'rxjs/operators';
import { LoadingHttpService } from 'varda-shared';

export interface PaginatorParams {
  cursor?: string | null;
  pageSize: number;
}

@Component({
    selector: 'app-varda-result-list',
    templateUrl: './varda-result-list.component.html',
    styleUrls: ['./varda-result-list.component.css'],
    standalone: false
})
export class VardaResultListComponent implements OnInit, OnChanges {
  @Input() resultCount: number;
  @Input() searchResults: Array<SearchResult>;
  @Input() pageSize: number;
  @Input() nextCursor: string | null;
  @Input() prevCursor: string | null;
  @Output() readonly resultSelected: EventEmitter<number> = new EventEmitter<number>();
  @Output() readonly paginationChanged: EventEmitter<PaginatorParams> = new EventEmitter<PaginatorParams>();

  paginatorParams: PaginatorParams = {
    pageSize: 20,
    cursor: null,
  };
  selectedId: number;
  isLoading: Observable<boolean>;

  constructor(private loadingHttpService: LoadingHttpService) {}

  ngOnInit() {
    this.isLoading = this.loadingHttpService.isLoading().pipe(delay(200));
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.searchResults && this.selectedId !== null) {
      this.selectResult(null);
    }

    if (changes.pageSize && this.pageSize) {
      this.paginatorParams.pageSize = this.pageSize;
    }
  }

  selectResult(resultId: number) {
    this.selectedId = resultId === this.selectedId ? null : resultId;
    this.resultSelected.emit(this.selectedId);
  }

  paginate(pageEvent: PageEvent) {
    if (pageEvent) {
      this.paginatorParams.pageSize = pageEvent.pageSize;

      const goingForward =
        pageEvent.previousPageIndex !== null &&
        pageEvent.pageIndex > pageEvent.previousPageIndex;

      if (goingForward) {
        if (this.nextCursor) {
          this.paginatorParams.cursor = this.nextCursor;
        }
      } else {
        if (this.prevCursor) {
          this.paginatorParams.cursor = this.prevCursor;
        }
      }
      this.paginationChanged.emit(this.paginatorParams);
    }

  }

  resetResults() {
    delete this.paginatorParams.cursor;  // go back to first page
  }
}
