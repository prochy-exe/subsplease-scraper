import requests, re, os
script_folder = os.path.dirname(os.path.abspath(__file__))
days = {
    "Monday": 1,
    "Tuesday": 2,
    "Wednesday": 3,
    "Thursday": 4,
    "Friday": 5,
    "Saturday": 6,
    "Sunday": 0
}

def generate_cron():
    crons = ''
    # URL of the webpage
    url = "https://subsplease.org/api/?f=schedule&tz=Etc/UTC"
    # Send a GET request to the URL
    response = requests.get(url)
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content
        schedule = response.json()['schedule']
        for day in schedule:
            for anime in schedule[day]:
                time = anime['time'].split(":")
                minutes = int(time[1]) + 5
                if minutes > 60:
                    minutes = minutes - 60
                elif minutes == 60:
                    minutes = 0
                crons += f"    - cron: '{minutes} {int(time[0])} * * {days[day]}' # {anime['title']}\n"
        return crons

def replace_existing_cron(action_data, cron):
    regex = (r".*schedule:\n"
	r"(.*)  work.*")
    regex = re.compile(regex, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    match = re.match(regex, action_data)
    sanitize_regex =  match.group(1).replace("*", r"\*")
    matched_regex = re.compile(sanitize_regex, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    replace = re.sub(matched_regex, cron, action_data) 
    return replace

if __name__ == "__main__":
    cron = generate_cron()
    with open(os.path.join(script_folder, ".github/workflows/update_database.yml"), "r+") as f:
        data = f.read()
        updated_action = replace_existing_cron(data, cron)
        f.seek(0)
        f.write(updated_action)
        f.truncate()