import { Component, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Title } from '@angular/platform-browser';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'huoltaja-app';

  constructor(
    private translateService: TranslateService,
    private titleService: Title
  ) {
    this.translateService.setDefaultLang('fi');
    this.translateService.use('fi');
  }

  ngOnInit() {
    this.translateService.get('page.title').subscribe(name => {
      this.titleService.setTitle(name);
    });
  }
}
