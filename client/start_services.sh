#!/bin/bash

# Change runtime env-variables
if [[ $VARDA_ENVIRONMENT_TYPE == *"public"* ]]; then
  sed -i "s/VARDA_FRONTEND_HOSTNAME/$VARDA_FRONTEND_HOSTNAME/g" /usr/share/nginx/html/varda/julkinen/main.*.js;
  sed -i "s/VARDA_BACKEND_HOSTNAME/$VARDA_BACKEND_HOSTNAME/g" /usr/share/nginx/html/varda/julkinen/main.*.js
else
  sed -i "s/VARDA_FRONTEND_HOSTNAME/$VARDA_FRONTEND_HOSTNAME/g" /usr/share/nginx/html/varda/main.*.js
  sed -i "s/VARDA_BACKEND_HOSTNAME/$VARDA_BACKEND_HOSTNAME/g" /usr/share/nginx/html/varda/main.*.js
fi



# Finally, start Nginx
echo Starting Nginx.
exec nginx -g "daemon off;"
