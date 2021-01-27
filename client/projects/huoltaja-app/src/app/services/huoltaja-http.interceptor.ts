import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor
} from '@angular/common/http';
import { Observable } from 'rxjs';
import { OppijaRaamitService } from './oppija-raamit.service';

@Injectable()
export class HuoltajaHttpInterceptor implements HttpInterceptor {

  constructor(private oppijaRaamitService: OppijaRaamitService) { }

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    this.oppijaRaamitService.clearLogoutInterval();
    return next.handle(request);
  }
}
