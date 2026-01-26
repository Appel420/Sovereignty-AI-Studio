# Make sure that you have a stable internet connection
status_dict = {}
# sample websites
websites = [
    import requests

status_dict =

# sample websites
websites = def check_websites(websites):
    for item in websites:
        website = item.strip()
        try:
            status = requests.get(website, timeout=5).status_code
            status_dict = "UP" if status == 200 else f"DOWN ({status})"
        except requests.exceptions.RequestException:
            status_dict = "DOWN (error)"
    print("Website".ljust(40), "Status")
    print("-" * 50)
    for site, s in status_dict.items():
        print(site.ljust(40), s)

check_websites(websites)
]

def check_websites(websites):
    for item in websites:
        website = item.strip()
        status = requests.get(website).status_code
        status_dict[website] = "UP" if status == 200 else "DOWN"
    print({"Website": "Status"})
    print("\n")
    print(status_dict)


check_websites(websites)
