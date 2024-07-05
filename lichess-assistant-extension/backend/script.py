import sys

def fetch_user_data(username):
    print(f"Fetching data for {username}")

if __name__ == "__main__":
    username = sys.argv[1]
    fetch_user_data(username)
