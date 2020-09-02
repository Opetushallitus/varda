import { Component, Inject, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from './core/auth/auth.service';
import { VardaDomService } from './core/services/varda-dom.service';
import { DOCUMENT } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { Router, NavigationEnd } from '@angular/router';
import { LoadingHttpService } from 'varda-shared';
import { Observable } from 'rxjs';
import { delay } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'app';
  isLoading: Observable<boolean>;

  constructor(
    private titleService: Title,
    private router: Router,
    private translateService: TranslateService,
    private auth: AuthService,
    private vardaDomService: VardaDomService,
    private loadingHttpService: LoadingHttpService,
    @Inject(DOCUMENT) private _document: any) {

    this.auth.loggedInUserAsiointikieliSet().subscribe((asiointikieli: string) => {
      const selectedAsiointikieli = (asiointikieli.toLocaleLowerCase() === 'sv') ? 'sv' : 'fi';
      this._document.documentElement.lang = selectedAsiointikieli;
      this.translateService.use(selectedAsiointikieli);
      this.setTitle(router);
    });

    const defaultLanguage = this.translateService.getBrowserLang() === 'sv' ? 'sv' : 'fi';
    this.translateService.setDefaultLang(defaultLanguage);
    this.translateService.use(defaultLanguage);
    this.vardaDomService.bindTabAndClickEvents();

    this.router.events.subscribe(event => {
      if (event instanceof NavigationEnd) {
        this.setTitle(router);
      }
    });

    this.isLoading = this.loadingHttpService.isLoading().pipe(delay(200));
  }

  ngOnInit() { }

  setTitle(router: Router): void {
    const title: string = this.getTitle(router.routerState, router.routerState.root).join('-');
    this.translateService.get(title).subscribe(
      translation => this.titleService.setTitle(`${translation} - Varda`)
    );
  }

  getTitle(state: any, parent: any): string[] {
    const data = [];
    if (parent && parent.snapshot.data && parent.snapshot.data.title) {
      data.push(parent.snapshot.data.title);
    }

    if (state && parent) {
      data.push(... this.getTitle(state, state.firstChild(parent)));
    }
    return data;
  }
}
