Install dependencies
```bash
pip install -r requirements.txt
```
Run migrations to setup database (NEVER COMMIT YOUR DB)

```bash
python manage.py makemigrations
python manage.py migrate
```

Start the simulation (greenhouse->management->commands)

You can change/add new configurations in the file.

```bash
python manage.py run_simulation
# Cold greenhouse (15°C, needs heating)
python manage.py run_simulation --config cold_start

# Hot and humid (30°C, needs cooling)
python manage.py run_simulation --config hot_humid

# Random conditions
python manage.py run_simulation --config random
```

Custom tick interval:
```bash
# Generate data every 10 seconds instead of 5
python manage.py run_simulation --interval 10
```

Continue without clearing data:
```bash
bashpython manage.py run_simulation --continue
```
