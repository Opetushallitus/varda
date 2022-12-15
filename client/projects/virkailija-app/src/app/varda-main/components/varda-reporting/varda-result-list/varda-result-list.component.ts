import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { LegacyPageEvent as PageEvent } from '@angular/material/legacy-paginator';
import { SearchResult } from '../varda-search-abstract.component';
import { Observable } from 'rxjs';
import { delay } from 'rxjs/operators';
import { LoadingHttpService } from 'varda-shared';

export interface PaginatorParams {
  pageSize: number;
  page: number;
}

@Component({
  selector: 'app-varda-result-list',
  templateUrl: './varda-result-list.component.html',
  styleUrls: ['./varda-result-list.component.css']
})
export class VardaResultListComponent implements OnInit, OnChanges {
  @Input() resultCount: number;
  @Input() searchResults: Array<SearchResult>;
  @Input() pageSize: number;
  @Output() readonly resultSelected: EventEmitter<number> = new EventEmitter<number>();
  @Output() readonly paginationChanged: EventEmitter<PaginatorParams> = new EventEmitter<PaginatorParams>();

  paginatorParams: PaginatorParams = {
    pageSize: 20,
    page: 1
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
    this.paginatorParams.page = pageEvent.pageIndex + 1;
    this.paginatorParams.pageSize = pageEvent.pageSize;

    this.paginationChanged.emit(this.paginatorParams);
  }

  resetResults() {
    this.paginatorParams.page = 1;
  }
}
