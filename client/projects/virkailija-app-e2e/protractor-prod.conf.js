// Protractor configuration file, see link for more information
// https://github.com/angular/protractor/blob/master/lib/config.ts

const { SpecReporter } = require('jasmine-spec-reporter');

exports.config = {
  params: {
    loginEnv: 'https://virkailija.testiopintopolku.fi/varda/login',
    login: {
      username: 'virkailija-b',
      password: 'IeGXRI^0%V24'
    }
  },
  allScriptsTimeout: 60000,
  specs: [
    './e2e/**/*.e2e-spec.ts'
  ],
  capabilities: {
    'directConnect': true,
    'browserName': 'chrome',
    'chromeOptions': {
      'args': ["--headless", "--disable-gpu"]
    },
  },
  directConnect: true,
  baseUrl: 'http://localhost:4200/',
  framework: 'jasmine',
  jasmineNodeOpts: {
    showColors: true,
    defaultTimeoutInterval: 60000,
    print: function() {}
  },
  onPrepare() {
    require('ts-node').register({
      project: 'e2e/tsconfig.e2e.json'
    });
    jasmine.getEnv().addReporter(new SpecReporter({ spec: { displayStacktrace: true } }));
  }
};
