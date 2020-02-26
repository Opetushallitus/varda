import { Component, Input, EventEmitter, Output, OnInit } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';

@Component({
  selector: 'app-varda-list-pagination',
  templateUrl: './varda-list-pagination.component.html',
  styleUrls: ['./varda-list-pagination.component.css']
})
export class VardaListPaginationComponent implements OnInit {
  @Input() prevLink: string | boolean;
  @Input() nextLink: string | boolean;
  @Input() currentPage: number = 1;
  @Input() maxPages: number;
  @Output() prevSearch = new EventEmitter(true);
  @Output() nextSearch = new EventEmitter(true);

  constructor(private loadingHttpService: LoadingHttpService) { }

  ngOnInit() {
  }

  searchPrev() {
    this.prevSearch.emit();
  }

  searchNext() {
    this.nextSearch.emit();
  }

  isLoading() {
    /* for this to work use LoadingHttpService instead of HttpService
      alternatively you can add *ngIf= to the component level to hide the buttons when wanted
    */
    return this.loadingHttpService.isLoading();
  }

}
