import { Injectable } from '@angular/core';
import { LoadingHttpService, UserHuollettavaDTO, VardaUserDTO, VardaApiServiceInterface } from 'varda-shared';
import { environment } from '../../environments/environment';
import { Observable, BehaviorSubject, forkJoin, of } from 'rxjs';
import { HuoltajaTranslations } from '../../assets/i18n/translations.enum';
import { HenkilotiedotDTO } from '../utilities/models/dto/henkilo-dto';
import { catchError, take } from 'rxjs/operators';
import { HuoltajaRoute } from '../utilities/models/enum/huoltaja-route.enum';
import {
  HuoltajatiedotDTO,
  HuoltajatiedotSimpleDTO,
  HuoltajuussuhdeSimpleDTO
} from '../utilities/models/dto/huoltajuussuhde-dto';
import { VarhaiskasvatustiedotDTO } from '../utilities/models/dto/lapsi-dto';
import { TyontekijatiedotDTO } from '../utilities/models/dto/tyontekija-dto';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class HuoltajaApiService implements VardaApiServiceInterface {
  oppijaApi = `${environment.huoltajaBackendUrl}/api/oppija`;
  loginApi = `${environment.huoltajaBackendUrl}/api/user`;

  private vardaDomains = ['opintopolku.fi', 'studieinfo.fi', 'studyinfo.fi'];

  private henkilot$ = new BehaviorSubject<Array<UserHuollettavaDTO>>(null);
  private henkilotiedot$ = new BehaviorSubject<HenkilotiedotDTO>(null); // the user or child selected
  private varhaiskasvatustiedot$ = new BehaviorSubject<VarhaiskasvatustiedotDTO>(null);
  private huoltajatiedot$ = new BehaviorSubject<HuoltajatiedotSimpleDTO>(null);
  private tyontekijatiedot$ = new BehaviorSubject<TyontekijatiedotDTO>(null);

  constructor(
    private http: LoadingHttpService,
    private router: Router
  ) { }

  getUserInfo(): Observable<VardaUserDTO> {
    return this.http.get(`${this.loginApi}/data/`);
  }

  fetchHenkilotiedot(henkilo_oid: string): Observable<HenkilotiedotDTO> {
    return this.http.get(`${this.oppijaApi}/v1/henkilotiedot/${henkilo_oid}/`);
  }

  fetchVarhaiskasvatustiedot(henkilo_oid: string): Observable<VarhaiskasvatustiedotDTO> {
    return this.http.get(`${this.oppijaApi}/v1/varhaiskasvatustiedot/${henkilo_oid}/`);
  }

  fetchHuoltajatiedot(henkilo_oid: string): Observable<HuoltajatiedotDTO> {
    return this.http.get(`${this.oppijaApi}/v1/huoltajatiedot/${henkilo_oid}/`);
  }

  fetchTyontekijatiedot(henkilo_oid: string): Observable<TyontekijatiedotDTO> {
    return this.http.get(`${this.oppijaApi}/v1/tyontekijatiedot/${henkilo_oid}/`);
  }

  getRoute(henkilo_oid: string): Observable<HuoltajaRoute> {
    return new Observable(routeObs =>
      forkJoin({
        henkilotiedot: this.fetchHenkilotiedot(henkilo_oid).pipe(catchError(() => of(null))),
        varhaiskasvatustiedot: this.fetchVarhaiskasvatustiedot(henkilo_oid).pipe(catchError(() => of(null))),
        huoltajatiedot: this.fetchHuoltajatiedot(henkilo_oid).pipe(catchError(() => of(null))),
        tyontekijatiedot: this.fetchTyontekijatiedot(henkilo_oid).pipe(catchError(() => of(null))),
      }).pipe(take(1)).subscribe({
        next: (results) => {
          const henkilotiedot: HenkilotiedotDTO = results.henkilotiedot;
          const varhaiskasvatustiedot: VarhaiskasvatustiedotDTO = results.varhaiskasvatustiedot;
          const huoltajatiedot: HuoltajatiedotSimpleDTO = this.combineHuoltajatiedot(results.huoltajatiedot);
          const tyontekijatiedot: TyontekijatiedotDTO = results.tyontekijatiedot;

          this.henkilotiedot$.next(henkilotiedot);
          this.varhaiskasvatustiedot$.next(varhaiskasvatustiedot);
          this.huoltajatiedot$.next(huoltajatiedot);
          this.tyontekijatiedot$.next(tyontekijatiedot);

          const urlPart = this.router.url.split('?').shift().split('/')?.[1];
          const currentRoute: HuoltajaRoute = HuoltajaRoute[urlPart];
          const allowedRoutes = [];

          if (tyontekijatiedot?.tyontekijat) {
            allowedRoutes.push(HuoltajaRoute.tyontekijatiedot);
          }

          if (huoltajatiedot?.huoltajuussuhteet) {
            allowedRoutes.push(HuoltajaRoute.huoltajuussuhteet);
          }

          if (varhaiskasvatustiedot?.lapset) {
            allowedRoutes.push(HuoltajaRoute.varhaiskasvatustiedot);
          }

          // stay at the current route on refresh if possible
          if (allowedRoutes.includes(currentRoute)) {
            routeObs.next(currentRoute);
          } else {
            routeObs.next(allowedRoutes?.[0] || HuoltajaRoute.ei_tietoja);
          }

          routeObs.complete();
        }, error: (err) => {
          routeObs.next(HuoltajaRoute.ei_tietoja);
          routeObs.complete();
        }
      })
    );
  }

  combineHuoltajatiedot(huoltajatiedot?: HuoltajatiedotDTO): HuoltajatiedotSimpleDTO {
    if (!huoltajatiedot) {
      return null;
    }

    // Merge huoltajuussuhde objects based on henkilo_id and vakatoimija_id/oma_organisaatio_id
    const huoltajuussuhdeList = huoltajatiedot.huoltajuussuhteet?.reduce(
      (previousValue: Array<HuoltajuussuhdeSimpleDTO>, currentValue) => {
        const existingHuoltajuussuhde = previousValue.find(huoltajuussuhde =>
          huoltajuussuhde.lapsi_henkilo_id === currentValue.lapsi_henkilo_id &&
          huoltajuussuhde.organisaatio_id === (currentValue.vakatoimija_id || currentValue.oma_organisaatio_id));

        if (existingHuoltajuussuhde) {
          existingHuoltajuussuhde.maksutiedot.push(...currentValue.maksutiedot);
        } else {
          previousValue.push({
            ...currentValue,
            organisaatio_id: currentValue.vakatoimija_id || currentValue.oma_organisaatio_id,
            organisaatio_nimi: currentValue.vakatoimija_nimi || currentValue.oma_organisaatio_nimi
          });
        }
        return previousValue;
      }, []);

    return {
      huoltaja_id: huoltajatiedot.huoltaja_id,
      huoltajuussuhteet: huoltajuussuhdeList
    };
  }

  setHenkilot(henkilot: Array<UserHuollettavaDTO>) {
    this.henkilot$.next(henkilot);
  }

  getHenkilot(): Observable<Array<UserHuollettavaDTO>> {
    return this.henkilot$.asObservable();
  }

  getHenkilotiedot(): Observable<HenkilotiedotDTO> {
    return this.henkilotiedot$.asObservable();
  }

  getVarhaiskasvatustiedot(): Observable<VarhaiskasvatustiedotDTO> {
    return this.varhaiskasvatustiedot$.asObservable();
  }

  getHuoltajatiedot(): Observable<HuoltajatiedotSimpleDTO> {
    return this.huoltajatiedot$.asObservable();
  }

  getTyontekijatiedot(): Observable<TyontekijatiedotDTO> {
    return this.tyontekijatiedot$.asObservable();
  }

  getVardaDomains(): Array<string> {
    return this.vardaDomains;
  }

  getTranslationCategory(): string {
    return environment.localizationCategory;
  }

  getLocalizationApi(): string {
    return `${environment.huoltajaBackendUrl}/api/julkinen/v1/localisation`;
  }

  getTranslationEnum(): any {
    return HuoltajaTranslations;
  }


  sortByAlkamisPaattymisPvm(list: Array<{ alkamis_pvm?: string; paattymis_pvm?: string }>) {
    list.sort((a, b) => {
      const compareA = a.paattymis_pvm ? `${a.alkamis_pvm}-${a.paattymis_pvm}` : `X${a.alkamis_pvm}`;
      const compareB = b.paattymis_pvm ? `${b.alkamis_pvm}-${b.paattymis_pvm}` : `X${b.alkamis_pvm}`;
      return compareB.localeCompare(compareA);
    });
  }
}
