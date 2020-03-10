import { browser, by, element, ElementFinder, protractor, ElementHelper } from 'protractor';

export const utils = {
    waitForElement(elem: ElementFinder, sleep = 15000): void {
        browser.wait(protractor.ExpectedConditions.presenceOf(elem), sleep);
    },

    clickElement(elem: ElementFinder, sleep = 15000): void {
        this.waitForElement(elem, sleep);
        elem.getText().then(function (text) {
            console.log('"' + text + '" presented, now waiting to be clickable');
        });
        browser.wait(protractor.ExpectedConditions.elementToBeClickable(elem), sleep);
        elem.getText().then(function (text) {
            console.log('"' + text + '" clicked, now sleeping ' + sleep);
        });
        elem.click();

        browser.sleep(1000);
    },

    selectNextDropdownOption(elem): void {
        utils.clickElement(elem);
        browser.actions().sendKeys(protractor.Key.ARROW_DOWN).perform();
        browser.actions().sendKeys(protractor.Key.ENTER).perform();
    },

    closeCookieButton(): void {
        const closeCookieButton = element(by.css('a[aria-label="dismiss cookie message"]'));
        closeCookieButton.isDisplayed().then(function (isDisplayed) {
            if (isDisplayed) {
                closeCookieButton.click();
            }
        });
    },

    selectDropdownOptionByText(elem, text): void {
        utils.clickElement(elem);
        elem.sendKeys(text);
        browser.actions().sendKeys(protractor.Key.ENTER).perform();
    },

    searchByCssStyle(elementFinder, desiredText) {
        const searchForStyle = function() {
            return elementFinder.getAttribute('style').then(function(actualStyleResultedFromAPromise) {
                return actualStyleResultedFromAPromise && actualStyleResultedFromAPromise === desiredText;
            });
        };
        return protractor.ExpectedConditions.and(protractor.ExpectedConditions.presenceOf(elementFinder), searchForStyle);
    }
};
