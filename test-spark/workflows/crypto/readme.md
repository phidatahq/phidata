## Crypto workflows

### Test DAGs

```sh
# ssh into airflow-ws or airflow-worker or databox
docker exec -it airflow-worker-container zsh

# List DAGs
airflow dags list

# List tasks
airflow tasks list -t crypto_prices_aws

# Test tasks
airflow tasks test \
  crypto_prices_aws \
  load_prices \
  2023-01-10

airflow tasks test \
  crypto_prices_aws \
  analyze_prices \
  2023-01-10

# Test tasks for ds + hour
airflow tasks test \
  crypto_prices_aws \
  load_prices \
  2023-01-10T01
```
