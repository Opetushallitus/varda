import { NgModule, Optional, SkipSelf } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedModule } from '../shared/shared.module';
import { VardaApiService } from './services/varda-api.service';
import { VardaLocalstorageWrapperService } from './services/varda-localstorage-wrapper.service';
import { VardaFormService } from './services/varda-form.service';
import { VardaApiWrapperService } from './services/varda-api-wrapper.service';
import { VardaVakajarjestajaService } from './services/varda-vakajarjestaja.service';
import { VardaUtilityService } from './services/varda-utility.service';
import { VardaModalService } from './services/varda-modal.service';
import { VardaValidatorService } from './services/varda-validator.service';
import { VardaRuleService } from './services/varda-rule.service';
import { VardaKielikoodistoService } from './services/varda-kielikoodisto.service';
import { VardaErrorMessageService } from './services/varda-error-message.service';
import { VardaDomService } from './services/varda-dom.service';
import { VardaKuntakoodistoService } from './services/varda-kuntakoodisto.service';

@NgModule({
  imports: [
    CommonModule,
    SharedModule
  ],
  providers: [
    VardaApiService,
    VardaLocalstorageWrapperService,
    VardaFormService,
    VardaApiWrapperService,
    VardaVakajarjestajaService,
    VardaUtilityService,
    VardaModalService,
    VardaValidatorService,
    VardaRuleService,
    VardaKielikoodistoService,
    VardaErrorMessageService,
    VardaDomService,
    VardaKuntakoodistoService
  ]
})
export class CoreModule {
  constructor (@Optional() @SkipSelf() parentModule: CoreModule) {
    if (parentModule) {
      throw new Error(
        'CoreModule is already loaded. Import it in the AppModule only');
    }
  }
}
