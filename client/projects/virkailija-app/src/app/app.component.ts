import { Component, Inject, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from './core/auth/auth.service';
import { VardaDomService } from './core/services/varda-dom.service';
import { DOCUMENT } from '@angular/common';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'app';

  constructor(
    private translateService: TranslateService,
    private auth: AuthService,
    private vardaDomService: VardaDomService,
    @Inject(DOCUMENT) private _document: any) {

    this.auth.loggedInUserAsiointikieliSet().subscribe((asiointikieli: string) => {
      const selectedAsiointikieli = (asiointikieli.toLocaleLowerCase() === 'sv') ? 'sv' : 'fi';
      this._document.documentElement.lang = selectedAsiointikieli;
      this.translateService.use(selectedAsiointikieli);
    });

    this.translateService.setDefaultLang('fi');
    this.translateService.use('fi');

    this.vardaDomService.bindTabAndClickEvents();
  }

  ngOnInit() {}
}
