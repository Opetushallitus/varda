import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, CanActivateChild, Router } from '@angular/router';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';
import { UserAccessKeys } from '../../utilities/models/varda-user-access.model';
import { take } from 'rxjs/operators';

@Injectable()
export class RoleGuard implements CanActivate, CanActivateChild {
  constructor(
    private authService: AuthService,
    private router: Router,
  ) { }

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean> | Promise<boolean> | boolean {
    return this.checkActivation(route, state);
  }

  canActivateChild(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean> | Promise<boolean> | boolean {
    return this.checkActivation(route, state);
  }

  private checkActivation(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean> | Promise<boolean> | boolean {
    return new Observable((roleGuardObs) => {
      const roles: Array<UserAccessKeys> = route.data.roles;
      const toimijaRoles: Array<UserAccessKeys> = route.data.toimijaRoles;
      if (!roles && !toimijaRoles) {
        roleGuardObs.next(true);
        roleGuardObs.complete();
      }

      this.authService.getToimipaikkaAccessToAnyToimipaikka().pipe(take(1)).subscribe({
        next: userAccessToAnyToimipaikka => {
          const toimijaAccess = this.authService.getUserAccess();
          const hasAccess = !!roles?.find(accessKey => userAccessToAnyToimipaikka[accessKey].katselija);
          const hasToimijaAccess = !!toimijaRoles?.find(accessKey => toimijaAccess[accessKey].katselija);

          roleGuardObs.next(hasAccess || hasToimijaAccess);
          roleGuardObs.complete();

          if ((roles || toimijaRoles) && !(hasAccess || hasToimijaAccess)) {
            this.router.navigate(['**'], { skipLocationChange: true, queryParams: { url: state.url } });
          }
        }, error: err => {
          roleGuardObs.next(false);
          roleGuardObs.complete();
        }
      });
    });
  }
}
