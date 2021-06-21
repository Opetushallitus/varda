import { Component, OnInit } from '@angular/core';
import { Location } from '@angular/common';
import { environment } from 'projects/virkailija-app/src/environments/environment';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-page-not-found',
  templateUrl: './page-not-found.component.html',
  styleUrls: ['./page-not-found.component.css']
})
export class PageNotFoundComponent implements OnInit {
  rootUrl: string;

  constructor(
    private activatedRoute: ActivatedRoute,
    private location: Location
  ) {
    this.rootUrl = environment.vardaFrontendUrl;
  }

  ngOnInit() {
    const replaceUrl = this.activatedRoute.snapshot.queryParams.url;
    if (replaceUrl) {
      this.location.replaceState(replaceUrl);
    }
  }
}
