// The file contents for the current environment will overwrite these during build.
// The build system defaults to the dev environment which uses `environment.ts`, but if you do
// `ng build --env=prod` then `environment.prod.ts` will be used instead.
// The list of which env maps to which file can be found in `.angular-cli.json`.

const vardaApiKeyUrl = 'http://localhost:8000/api/user/apikey/';
const vardaApiUrl = 'http://localhost:8000/api/v1';
const vardaAppUrl = 'http://localhost:8000';
const vardaFrontendUrl = 'http://localhost:4200';
// Below variables are only for test environment / production use
const virkailijaOpintopolkuUrl = '';
const virkailijaTestiOpintopolkuUrl = 'https://virkailija.testiopintopolku.fi';
const virkailijaRaamitScriptPath = '/virkailija-raamit/apply-raamit.js';
const localizationCategory = 'varda-virkailija';

export const environment = {
  vardaApiKeyUrl,
  vardaApiUrl,
  vardaAppUrl,
  vardaFrontendUrl,
  virkailijaOpintopolkuUrl,
  virkailijaTestiOpintopolkuUrl,
  virkailijaRaamitScriptPath,
  localizationCategory,
  useLocalStorage: false,
  production: false
};
