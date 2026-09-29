import os
from app.config import get_settings
from app.repositories import PostgresRepository

def main() -> None:
    repository = PostgresRepository(get_settings().database_url)
    repository.migrate()
    repository.seed_demo(os.getenv("DEMO_TENANT_A_API_KEY", "demo-tenant-a-key"), os.getenv("DEMO_TENANT_B_API_KEY", "demo-tenant-b-key"))
    print("Seeded Demo Tenant A and Demo Tenant B.")

if __name__ == "__main__":
    main()
