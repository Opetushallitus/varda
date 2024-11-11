# Stage 0, based on Node.js, to build and compile Angular
FROM 105387356358.dkr.ecr.eu-west-1.amazonaws.com/ecr-public/docker/library/node:20 as node
WORKDIR /app
# Install dependencies first to leverage Docker caching
COPY package*.json ./
RUN npm install
# Copy and build rest of the app
ARG project=virkailija-app
COPY . ./
RUN npm run ng -- build varda-shared && npm run build -- ${project} && \
    chmod -R 777 /app/dist/${project}

# Stage 1, based on Nginx, to have only the compiled app, ready for production with Nginx
FROM 105387356358.dkr.ecr.eu-west-1.amazonaws.com/docker-base/nginx-lua:20240902
ARG project=virkailija-app

# forward request and error logs to docker log collector
RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log && \
    touch /var/run/nginx.pid && \
    chown -R www-data:www-data /var/run/nginx.pid && \
    chown -R www-data:www-data /var/cache/nginx && \
    chmod -R 777 /var/log/nginx /var/cache/nginx /var/run /usr/share/nginx/html/varda && \
    mkdir -p /tmp/${project}

COPY --from=node /app/dist/${project} /tmp/${project}

RUN if [ "$project" = "public-app" ]; \
    then cp -R /tmp/${project} /usr/share/nginx/html/varda/julkinen; chmod -R 777 /usr/share/nginx/html/varda/julkinen; \
    elif [ "$project" = "pulssi-app" ]; \
    then cp -R /tmp/${project} /usr/share/nginx/html/varda/pulssi; chmod -R 777 /usr/share/nginx/html/varda/pulssi; \
    else cd /tmp/${project}; cp -R . /usr/share/nginx/html/varda; \
    fi
# We need to introduce our environment variables on root level
COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./nginx-custom.conf /etc/nginx/conf.d/default.conf
COPY ./nginx-proxy.conf /etc/nginx/app/nginx-proxy.conf
COPY ./nginx.lua /opt/varda-lua/varda.lua

# Give read/write permissions for everyone in /etc/nginx/conf.d/ so sed can replace template variables
# TODO: do replacement already during build process to be safe
RUN chmod -R ugo+rw /etc/nginx/conf.d

COPY start_services.sh /start_services.sh
# Give execute permissions for start_services.sh
RUN chmod -R ugo+x /start_services.sh

EXPOSE 8080

STOPSIGNAL SIGQUIT

USER 1001

# CMD specifies the command to execute to start the services.
CMD ["/start_services.sh"]
# done!
