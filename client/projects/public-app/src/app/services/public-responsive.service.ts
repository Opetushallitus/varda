import { Injectable } from '@angular/core';
import { BreakpointObserver } from '@angular/cdk/layout';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class PublicResponsiveService {
  private isSmallSubject: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  private isExtraSmallSubject: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  constructor(private breakpointObserver: BreakpointObserver) {
    this.breakpointObserver.observe('(min-width: 992px)').subscribe(data => {
      this.isSmallSubject.next(!data.matches);
    });
    this.breakpointObserver.observe('(min-width: 768px)').subscribe(data => {
      this.isExtraSmallSubject.next(!data.matches);
    });
  }

  getIsSmall(): BehaviorSubject<boolean> {
    return this.isSmallSubject;
  }

  getIsExtraSmall(): BehaviorSubject<boolean> {
    return this.isExtraSmallSubject;
  }
}
