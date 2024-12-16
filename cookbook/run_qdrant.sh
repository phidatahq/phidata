docker run -p 6333:6333 \
  -d \
  -v qdrant-volume:/qdrant/storage \
  --name qdrant \
  qdrant/qdrant
