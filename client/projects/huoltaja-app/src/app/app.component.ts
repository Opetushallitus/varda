import { Component, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Title } from '@angular/platform-browser';
import { LoadingHttpService } from 'varda-shared';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'huoltaja-app';
  initialized: boolean;

  constructor(
    private translateService: TranslateService,
    private titleService: Title,
    private loadingHttpService: LoadingHttpService
  ) {
    this.translateService.setDefaultLang('fi');
    this.translateService.use('fi');
  }

  isLoading(): boolean {
    return this.loadingHttpService.isLoading();
  }

  ngOnInit() {
    this.initialized = true;
    this.translateService.get('page.title').subscribe(name => {
      this.titleService.setTitle(name);
    });
  }
}
