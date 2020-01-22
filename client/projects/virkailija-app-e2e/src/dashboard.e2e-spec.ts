import { DashboardPage } from './pageobjects/dashboard.po';
import { browser, protractor} from 'protractor';

describe('Dashboard e2e-tests', () => {
  let dashboardPage: DashboardPage;

  beforeEach(() => {
    dashboardPage = new DashboardPage();
    dashboardPage.navigateToDashboard();
  });

  describe('Dashboard - Default view', () => {
    const ec = protractor.ExpectedConditions;

    it('Should have main elements in place on dashboard page', () => {
      browser.wait(ec.presenceOf(dashboardPage.vardaHeaderLinks.get(0)), 20000, 'Etusivu-link did not appear in DOM in 20 seconds');
      const etusivuLink = dashboardPage.vardaHeaderLinks.get(0);
      const vakaToimijaLink = dashboardPage.vardaHeaderLinks.get(1);
      const tietojenKatseluLink = dashboardPage.vardaHeaderLinks.get(2);
      const ohjeetLink = dashboardPage.vardaHeaderLinks.get(3);

      expect(etusivuLink.getText()).toEqual('ETUSIVU');
      expect(vakaToimijaLink.getText()).toEqual('TOIMIJAN TIEDOT');
      expect(tietojenKatseluLink.getText()).toEqual('TIETOJEN KATSELU');
      expect(ohjeetLink.getText()).toEqual('OHJEET');
    });
  });

});
