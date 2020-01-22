# VARDA-Frontend

### Prerequisites
- node 8.x.x
- npm 6.x.x

### Optional
- Angular cli 7.x.x https://cli.angular.io/
- Docker

## Getting started

- `npm install -g @angular/cli@^7.0.0`
- `npm install`

## Running project

#### 1 Running against Webpack dev server (recommended)
- `ng build varda-shared`
  - If you do changes here you can do builds automatically with `ng build varda-shared --watch`
- `ng serve`
  - There are multiple projects but default is virkailija-app. To run certain project `ng serve <project name>`
- See possible configurations `src/environments` and adjust according to your setup
- e.g run against local varda-backend service `ng serve --configuration=local` or against test-environment `ng serve`

#### 2 Running against nginx-proxy through docker container
- `docker build -t varda-fe .`
- `docker run -it --rm -e VARDA_SESSION_SECURE='' -e VARDA_FRONTEND_PROTOCOL='http' -e VARDA_FRONTEND_HOSTNAME='localhost' -e VARDA_BACKEND_HOSTNAME='<backend host>' -e VARDA_BACKEND_PROTOCOL='http' --name varda-frontend varda-fe`
- NOTE: live reload not available


### Authentication
- Get authentication token from the backend service and set it to browser `localStorage.setItem('varda.api.token', JSON.stringify({"token":"<token_value>","expiryTime": null});`. Refresh browser.
- **OR**
- Authenticate through CAS: Running both varda-frontend- and varda-container required. Login through login page.
