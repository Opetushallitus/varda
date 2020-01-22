import { browser, by, element } from 'protractor';

export class DashboardPage {

  vardaHeaderLinks: any;
  addToimipaikkaBtn: any;
  addHenkiloBtn: any;
  editToimipaikkaBtn: any;
  toimipaikkaSelector: any;

  async navigateToDashboard(): Promise<any> {
    browser.waitForAngularEnabled(false);
    if (browser.params.token) {
      this.doTokenLogin();
    } else {
      try {
        await this.doCASLogin();
      } catch (e) {
        // In case we are already logged in
        if (e.message.indexOf('Unable to locate element: {"method":"css selector","selector":"*[id="navigateToVardaLoginBtn"]') !== -1) {
          console.log('Already logged in');
        } else {
          throw e;
        }
      } finally {
        this.selectDashboadElements();
      }
    }
  }

  async doCASLogin(): Promise<any> {
    // Non angular app so we have to use promises
    await browser.get(browser.params.loginEnv);
    browser.sleep(500);
    const vardaLoginBtn = await browser.driver.findElement(by.id('navigateToVardaLoginBtn'));
    await vardaLoginBtn.click();
    browser.sleep(2000);
    browser.driver.findElement(by.id('username')).sendKeys(browser.params.login.username);
    browser.driver.findElement(by.id('password')).sendKeys(browser.params.login.password);
    await browser.driver.findElement(by.name('submit')).click();
    browser.sleep(4000);
    await browser.get(browser.params.loginEnv);
  }

  doTokenLogin(): any {
    return browser.get('/varda/').then(() => {
      browser
        .executeScript(`window.localStorage.
      setItem('varda.api.token', JSON.stringify({\"token\":\"${browser.params.token}\",\"expiryTime\": null}));`);
    }).then(() => browser.get('/varda/'));
  }

  selectDashboadElements(): void {
    this.vardaHeaderLinks = element.all(by.className('varda-header-nav-item-container'));
    this.addToimipaikkaBtn = element(by.id('addToimipaikkaBtn'));
    this.addHenkiloBtn = element(by.id('addHenkiloBtn'));
    this.editToimipaikkaBtn = element(by.id('editToimipaikkaBtn'));
    this.toimipaikkaSelector = element(by.id('toimipaikkaSelectorSelect'));
  }

}
