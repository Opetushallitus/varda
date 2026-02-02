# VARDA-Frontend

### Prerequisites
- node 20+
- npm 10+
- Angular cli 20.x.x https://cli.angular.io/

### Optional
- Docker

## Getting started

- `npm install -g @angular/cli` (installs latest version)
- `npm install` (in frontend folder)

## Running project

#### 1 Running against Webpack dev server (recommended)
- `ng build varda-shared`
  - If you do changes here you can do builds automatically with `ng build varda-shared --watch`
- `ng serve virkailija-app`
  - There are multiple projects, to run certain project `ng serve <project name>`
- See possible configurations `src/environments` and adjust according to your setup
- e.g run against local varda-backend service `ng serve --configuration=local` or against test-environment `ng serve`
- Running only the command `ng serve virkailija-app` will run the application against QA environment.

#### 2 Running against nginx-proxy through docker container
- `docker build --build-arg NPM_TOKEN=${NPM_TOKEN} -t varda-fe .`
- `docker run -it --rm -e VARDA_SESSION_SECURE='' -e VARDA_FRONTEND_PROTOCOL='http' -e VARDA_FRONTEND_HOSTNAME='localhost' -e VARDA_BACKEND_HOSTNAME='<backend host>' -e VARDA_BACKEND_PROTOCOL='http' --name varda-frontend varda-fe`
- NOTE: live reload not available

### Authentication
- Get authentication token from the backend service and set it to browser `localStorage.setItem('varda.api.token', JSON.stringify({"token":"<token_value>","expiryTime": null});`. Refresh browser.
- **OR**
- Authenticate through CAS: Running both varda-frontend- and varda-container required. Login through login page.

### Linting
  Eslint is used for linting. To run linting:
- `npm run lint` and `npm run lint:projects`

### New component
  If you want to create new component, use angular cli to generate it. Example in virkailija-app:
- `ng generate component <component-name> --path=projects/virkailija-app/src/app/varda-main/components/<component-name> --project virkailija-app `
- Use `ng generate --help` to see more options of what you can generate.

## Other

### Components
- [Angular Material](https://material.angular.io/components/categories) is used along with custom varda components.
  - Use angular material components when possible
- There are also custom made varda components in use which can be found in `shared` folders
  - E.g. applications/frontend/projects/virkailija-app/src/app/shared/components

### Translations
- [Lokaalisointipalvelu](https://virkailija.testiopintopolku.fi/lokalisointi/secured/index.html)
- Translation keys can be found in virkailija-translations.enum.ts for virkailija-app
- For every text we add to the application need to add a key and value
  - The key is then added to lokaalisointipalvelu with a value
- Example usage
  - Key: reminder_report_no_report = 'reminder-report.no-report',
  - HTML: {{i18n.reminder_report_no_report | translate}}

### Koodisto
- [Koodistopalvelu](https://virkailija.testiopintopolku.fi/koodisto-app/)
- Example usage
- [libKoodistoValue]="koodistoEnum.tuentaso"

### Angular DevTools
- Use [Angular Dev Tools](https://angular.io/guide/devtools) to help with development as it provides a lot of useful information about the application.
- It provides an easy way to find components, services, modules etc. in the application from the browser.
