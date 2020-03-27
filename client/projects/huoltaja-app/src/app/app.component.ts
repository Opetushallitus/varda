import { Component, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Title } from '@angular/platform-browser';
import { LoadingHttpService } from 'varda-shared';
import { Observable } from 'rxjs/internal/Observable';
import { delay } from 'rxjs/internal/operators/delay';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'huoltaja-app';
  isLoading: Observable<boolean>;

  constructor(
    private translateService: TranslateService,
    private titleService: Title,
    private loadingHttpService: LoadingHttpService
  ) {
    this.translateService.setDefaultLang('fi');
    this.translateService.use('fi');
    this.isLoading = this.loadingHttpService.isLoading().pipe(delay(200));
  }

  ngOnInit() {
    this.translateService.get('page.title').subscribe(name => {
      this.titleService.setTitle(name);
    });
  }
}
