# CAS authentication

All frontend users log in to Varda via Opintopolku **CAS** and **CAS-oppija**.
CAS is not maintained by Varda team.

CAS login utilizes the [django-cas-ng](https://github.com/django-cas-ng/django-cas-ng) CAS client
libary with some modifications to work with Opintopolku CAS.

## CAS

CAS is used for Varda virkailija/frontend user authentication. Service/API (palvelukäyttäjä) users
are authenticated with a custom basic authentication implementation. CAS login is common for all
services in Opintopolku.

CAS login process is as follows:
1. User initiates login in frontend
2. User is redirected to CAS login endpoint `/accounts/login/`
3. Frontend Nginx writes return location to the header `CAS_NEXT` and a verification hash to
   `CAS_NEXT_HASH` (this is passed to CAS so that it knows where to redirect after login)
4. User is redirected to CAS and logs in
5. User is redirected back to Varda with basic user information
6. User permissions and additional information are fetched from Opintopolku based on the
   username CAS returned
7. API token is sent back to frontend in a short-lived `token` cookie
8. Frontend continues to use this token in `Authorization` header

## CAS-oppija

CAS-oppija is used for citizen authentication. Citizens can log in to Varda without or
with e-authorization (valtuudet).

In normal case user logs in without e-authorization to access their own information stored in Varda.
E-authorization (valtuudet) enables logging in to Varda on behalf of someone else.
Basically a parent or guardian can log in "as" a child and view their information stored in Varda.

CAS-oppija login process is mostly similar to CAS login process:
1. User is redirected to CAS-oppija login endpoint `/accounts/huoltaja-login/`
2. `valtuudet` query parameter is passed to CAS-oppija, which determines whether user
   logs in with e-authorization or not
3. User is redirected back to Varda with possible e-authorization/impersonation information
4. User's `Z3_AdditionalCasUserFields.huollettava_oid_list` is updated if user logged in with
   e-authorization (this is used to validate if user has permissions to get information of some
   other person)
