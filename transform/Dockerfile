FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    dbt-bigquery==1.12.0

COPY dbt /app/dbt
COPY transform/run_dbt.sh /app/run_dbt.sh

RUN chmod +x /app/run_dbt.sh

ENTRYPOINT ["/app/run_dbt.sh"]