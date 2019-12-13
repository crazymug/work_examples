docker run -e POSTGRES_USER=g_umarov -e POSTGRES_PASSWORD=123 -p 5432:5432 -v /home/g_umarov/suir/db:/var/lib/postgresql/data -d postgres:11.2-alpine
