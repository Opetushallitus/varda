import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class MatomoService {

  constructor() { }

  initMatomo(siteID: number) {
    const node = document.createElement('script');
    node.id = 'matomo';
    node.type = 'text/javascript';
    node.async = true;
    node.innerHTML = `
    var _paq = window._paq || [];

    function matomoPageChange(title, path) {
      _paq.push(['setCustomUrl', path]);
      _paq.push(['setDocumentTitle', title]);
      _paq.push(['trackPageView']);
      _paq.push(['enableLinkTracking']);
    }

    (function() {
      var u="//analytiikka.opintopolku.fi/matomo/";
      _paq.push(['setTrackerUrl', u+'matomo.php']);
      _paq.push(['setSiteId', '${siteID}']);
      var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
      g.type='text/javascript'; g.id='matomoScript'; g.async=true; g.defer=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
    })();
    `;
    document.getElementsByTagName('html')[0].appendChild(node);
  }
}
