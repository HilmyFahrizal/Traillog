from database import init_database, seed_from_sql

print("Inisialisasi tabel...")
init_database()
print("Seed data awal...")
seed_from_sql()
print("Selesai!")