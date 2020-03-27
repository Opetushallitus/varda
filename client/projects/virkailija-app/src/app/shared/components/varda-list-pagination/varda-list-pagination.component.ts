import { Component, Input, EventEmitter, Output } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { Subscription, Observable } from 'rxjs';
import { delay } from 'rxjs/internal/operators/delay';

@Component({
  selector: 'app-varda-list-pagination',
  templateUrl: './varda-list-pagination.component.html',
  styleUrls: ['./varda-list-pagination.component.css']
})
export class VardaListPaginationComponent {
  @Input() prevLink: string | boolean;
  @Input() nextLink: string | boolean;
  @Input() currentPage = 1;
  @Input() maxPages: number;
  @Output() prevSearch = new EventEmitter(true);
  @Output() nextSearch = new EventEmitter(true);
  isLoading: Observable<boolean>;

  constructor(private loadingHttpService: LoadingHttpService) {
    this.isLoading = this.loadingHttpService.isLoading().pipe(delay(200));
  }

  searchPrev() {
    this.prevSearch.emit();
  }

  searchNext() {
    this.nextSearch.emit();
  }
}
