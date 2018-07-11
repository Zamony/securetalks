import gui
import storage

def main():
    db_path = pathlib.Path.home() / ".securetalks" / "db.sqlite3"
    seconds_in_two_days = 60 * 60 * 24 * 2
    storage = Storage(db_path, seconds_in_two_days)

    events = webevents.run(("localhost", 8080), "../web")

    storage.close()

if __name__ == "__main__":
    main()