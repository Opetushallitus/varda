import { Component, Inject, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from './core/auth/auth.service';
import { VardaDomService } from './core/services/varda-dom.service';
import { DOCUMENT } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { Router, NavigationEnd } from '@angular/router';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'app';

  constructor(
    private titleService: Title,
    private router: Router,
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


    this.router.events.subscribe(event => {
      if (event instanceof NavigationEnd) {
        let title: string = this.getTitle(router.routerState, router.routerState.root).join('-');
        this.translateService.get(title).subscribe(
          translation => this.titleService.setTitle(`${translation} - Varda`)
        )
      }
    });

  }

  ngOnInit() { }


  getTitle(state: any, parent: any) {
    var data = [];
    if (parent && parent.snapshot.data && parent.snapshot.data.title) {
      data.push(parent.snapshot.data.title);
    }

    if (state && parent) {
      data.push(... this.getTitle(state, state.firstChild(parent)));
    }
    return data;
  }
}
