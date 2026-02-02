import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, CanActivateChild, Router, RouterStateSnapshot } from '@angular/router';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';
import { UserAccessKeys, UserAccessTypes } from '../../utilities/models/varda-user-access.model';

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
      const accessType = !!route.data.requireTallentaja ? UserAccessTypes.tallentaja : UserAccessTypes.katselija;

      if (!roles && !toimijaRoles) {
        roleGuardObs.next(true);
        roleGuardObs.complete();
      }

      const userAccess = this.authService.anyUserAccess;
      const organisaatioUserAccess = this.authService.organisaatioUserAccess;

      const hasAccess = !!roles?.find(accessKey => userAccess[accessKey][accessType]);
      const hasToimijaAccess = !!toimijaRoles?.find(accessKey => organisaatioUserAccess[accessKey][accessType]);

      roleGuardObs.next(hasAccess || hasToimijaAccess);
      roleGuardObs.complete();

      if ((roles || toimijaRoles) && !(hasAccess || hasToimijaAccess)) {
        this.router.navigate(['**'], { skipLocationChange: true, queryParams: { url: state.url } });
      }
    });
  }
}
