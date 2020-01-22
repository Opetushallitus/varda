#!/bin/bash

# Change runtime env-variables
sed -i "s/VARDA_BACKEND_HOSTNAME/$VARDA_BACKEND_HOSTNAME/g" /usr/share/nginx/html/varda/main.*.js
sed -i "s/VARDA_FRONTEND_HOSTNAME/$VARDA_FRONTEND_HOSTNAME/g" /usr/share/nginx/html/varda/main.*.js

# Finally, start Nginx
echo Starting Nginx.
exec nginx -g "daemon off;"
