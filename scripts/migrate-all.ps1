$services = @(
  "staff",
  "manager",
  "customer",
  "catalog",
  "book",
  "cart",
  "order",
  "ship",
  "pay",
  "comment-rate",
  "recommender-ai",
  "api-gateway"
)

foreach ($svc in $services) {
  Write-Host "Running migrations for $svc..."
  docker compose run --rm $svc python manage.py makemigrations app
  docker compose run --rm $svc python manage.py migrate
}

Write-Host "All migrations finished."
