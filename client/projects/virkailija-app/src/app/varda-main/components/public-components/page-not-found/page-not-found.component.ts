import { Component, OnInit } from '@angular/core';
import { environment } from 'projects/virkailija-app/src/environments/environment';
@Component({
  selector: 'app-page-not-found',
  templateUrl: './page-not-found.component.html',
  styleUrls: ['./page-not-found.component.css']
})
export class PageNotFoundComponent implements OnInit {

  rootUrl: string;

  constructor() {
    this.rootUrl = environment.vardaFrontendUrl;
  }

  ngOnInit() {
  }

}
