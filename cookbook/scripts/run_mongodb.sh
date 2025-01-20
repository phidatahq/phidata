docker run -d \
  --name mongodb \
  -e MONGO_INITDB_DATABASE=ai \
  -e MONGO_INITDB_ROOT_USERNAME=ai \
  -e MONGO_INITDB_ROOT_PASSWORD=ai \
  -v mongo_data:/data/db \
  -v mongo_config:/data/configdb \
  -p 27017:27017 \
  mongo