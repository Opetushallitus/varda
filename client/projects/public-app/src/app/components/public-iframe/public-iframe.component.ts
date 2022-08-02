import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { environment } from '../../../environments/environment';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-public-iframe',
  templateUrl: './public-iframe.component.html',
  styleUrls: ['./public-iframe.component.css']
})
export class PublicIframeComponent implements OnChanges {
  @Input() autoHeight = true;
  @Input() url: string;
  trustedUrl: SafeResourceUrl;

  constructor(private domSanitizer: DomSanitizer) { }

  ngOnChanges(changes: SimpleChanges) {
    this.trustedUrl = this.domSanitizer.bypassSecurityTrustResourceUrl(`${environment.backendUrl}${this.url}`);
  }
}
