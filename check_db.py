import sqlite3

conn = sqlite3.connect("data/options_history.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM option_history")
print("Total records:", c.fetchone()[0])
c.execute(
    "SELECT DISTINCT DATE(scan_date) FROM option_history ORDER BY scan_date DESC LIMIT 10"
)
print("Scan dates:", [r[0] for r in c.fetchall()])
c.execute("SELECT DISTINCT underlying_symbol FROM option_history LIMIT 10")
print("Sample symbols:", [r[0] for r in c.fetchall()])
conn.close()
