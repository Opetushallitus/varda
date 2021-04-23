CREATE USER read_only_user WITH ENCRYPTED PASSWORD 'localhero';
GRANT CONNECT ON DATABASE varda TO read_only_user;
