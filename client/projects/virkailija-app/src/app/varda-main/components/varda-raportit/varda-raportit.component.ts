import { Component, OnDestroy } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';
import { AuthService } from '../../../core/auth/auth.service';


@Component({
  selector: 'app-varda-raportit',
  templateUrl: './varda-raportit.component.html',
  styleUrls: ['./varda-raportit.component.css']
})
export class VardaRaportitComponent implements OnDestroy {
  i18n = VirkailijaTranslations;
  pageHeader: string;
  activeLink: string;
  isOPHUser: boolean;
  subscriptions: Array<Subscription> = [];

  constructor(
    private authService: AuthService,
    private router: Router,
  ) {

    this.isOPHUser = this.authService.isOPHUser;

    this.subscriptions.push(
      this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe((navigation: NavigationEnd) => {
        this.setPage(this.router.routerState.root);
      })
    );

    this.setPage(this.router.routerState.root);
  }


  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  setPage(route: ActivatedRoute) {
    this.activeLink = this.router.url.split('?').shift().split('/')[2] || 'raportit'; // path is /raportit/{activeLink}/something
    let snapshot = route.snapshot;
    while (snapshot) {
      this.pageHeader = snapshot.data.title || this.pageHeader;
      snapshot = snapshot.firstChild;
    }
  }
}
