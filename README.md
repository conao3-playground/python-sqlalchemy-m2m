# python-sqlalchemy-m2m

## Run

### Prepare DB
```
docker compose up
```

```sql
create schema m2m;
```

### Install dependency

```
poetry install
```

### Prepare Data

```
poetry run python -m sqlalchemy_m2m.init_db
```


### Run

```
poetry run sqlalchemy-m2m main-1
```

There're main-{1-5} sample code.  See source file.
