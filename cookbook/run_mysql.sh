docker run -d \
  -e MYSQL_ROOT_PASSWORD=phi \
  -e MYSQL_DATABASE=phi \
  -e MYSQL_USER=phi \
  -e MYSQL_PASSWORD=phi \
  -p 3306:3306 \
  -v mysql_data:/var/lib/mysql \
  -v $(pwd)/cookbook/mysql-init:/docker-entrypoint-initdb.d \
  --name mysql \
  mysql:8.0
