import { Component, Inject, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { VardaDomService } from './core/services/varda-dom.service';
import { DOCUMENT } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { Router, NavigationEnd } from '@angular/router';
import { LoadingHttpService, LoginService, VardaKoodistoService, VardaUserDTO } from 'varda-shared';
import { interval, Observable } from 'rxjs';
import { delayWhen, filter } from 'rxjs/operators';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  isLoading: Observable<boolean>;

  constructor(
    private titleService: Title,
    private router: Router,
    private translateService: TranslateService,
    private koodistoService: VardaKoodistoService,
    private vardaDomService: VardaDomService,
    private loadingHttpService: LoadingHttpService,
    private loginService: LoginService,
    @Inject(DOCUMENT) private _document: any) {

    this.initKoodistotAndLanguage();

    this.router.events.subscribe(event => {
      if (event instanceof NavigationEnd) {
        this.setTitle(router);
      }
    });

    this.isLoading = this.loadingHttpService.isLoadingWithDebounce();
  }

  ngOnInit() { }

  setTitle(router: Router): void {
    const title: string = this.getTitle(router.routerState, router.routerState.root).join('-') || 'Varda';
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


  initKoodistotAndLanguage() {
    const defaultLanguage = this.translateService.getBrowserLang() === 'sv' ? 'sv' : 'fi';
    this.translateService.setDefaultLang(defaultLanguage);
    this.translateService.use(defaultLanguage);
    this.vardaDomService.bindTabAndClickEvents();

    this.loginService.getCurrentUser().pipe(filter(Boolean)).subscribe((user: VardaUserDTO) => {
      const userLanguage = user.asiointikieli_koodi.toLocaleLowerCase() === 'sv' ? 'sv' : 'fi';
      this._document.documentElement.lang = userLanguage;
      this.translateService.use(userLanguage);
      this.setTitle(this.router);
      this.koodistoService.initKoodistot(environment.vardaAppUrl, userLanguage);
    });
  }
}




