select pg_terminate_backend(pid) from pg_stat_activity where datname='varda';
drop database varda;
create database varda with owner varda_db_user;
