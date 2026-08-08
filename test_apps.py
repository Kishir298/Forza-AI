from tools.app_manager import AppManager

manager = AppManager()

print(f"\nFound {len(manager.apps)} apps.\n")

while True:

    query = input("Search: ")

    matches = manager.search(query)

    print()

    for app, score in matches:

        print(f"{app['name']} ({score:.1f})")

    print()
