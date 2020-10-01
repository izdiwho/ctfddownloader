#! python3
import re
import os
import sys
import time
import json
import glob
import datetime
import urllib3
from getpass import getpass
import requests
from pprint import pprint
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver

# CONSTANTS #
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
nonce_pattern = re.compile("[a-f0-9]{64}")
path = os.getcwd()

# VARIABLES #
if (len(sys.argv) != 4):
    print("usage: python autoctfd.py https://ctf_url username action(setup, submit, challs, scores, sscores, solves)")
    exit()

# FUNCTIONS #


def login(session, base_url, username, password):
    failed = re.compile("Your username or password is incorrect")
    r = req(session, "post", "/login", d={'name': username,
                                          'password': password,
                                          'nonce': csrf_token(session, base_url)})
    if (len(failed.findall(r.text)) > 0):
        print("Wrong username or password")
        exit()


def grab_challenges(path, session):
    print("Grabbing challenges...")
    challenges_g = req(session, "get", "/api/v1/challenges")
    challenges = challenges_g.json()["data"]

    print("Found %s challenges" % len(challenges))
    for i, v in enumerate(challenges):
        chall_g = req(session, "get", "/api/v1/challenges/" + str(v["id"]))
        create_challenge(path, session, chall_g.json()["data"])
    print("Done!")
    session.close()


def submit_flags(path, session):
    print("Submitting flags from flag.txt files every 5 seconds")
    while True:
        try:
            id_files = find_files('id', path)
            if len(find_files('flag.txt', path)) > 0:
                flag_files = find_files('flag.txt', path)
            if len(find_files('flag', path)) > 0:
                flag_files = find_files('flag', path)

            flags = dict()
            for i, v in enumerate(id_files):
                with open(v, 'r') as f:
                    flag_file = open(flag_files[i], 'r')
                    flag = flag_file.read()
                    if (flag != ''):
                        flags[f.read()] = flag.splitlines()[0]
                    flag_file.close()

            if len(flags) > 0:
                for id, flag in flags.items():
                    r = req(session, "jpost", "/api/v1/challenges/attempt",
                            j={"challenge_id": id, "submission": flag}).json()
                    if r["success"]:
                        print("Submission for challenge ID %s is %s" %
                              (id, r["data"]["status"]))
            time.sleep(5)
        except KeyboardInterrupt:
            print("Done!")
            session.close()
            exit()


def grab_scores(path, session):
    print("Grabbing scores...")
    # Set up screenshot folder
    sc_path = path / "screenshots"
    create_dir(sc_path)
    st = datetime.datetime.fromtimestamp(
        time.time()).strftime('%Y-%m-%d_%H-%M')
    st_path = sc_path / st
    create_dir(st_path)
    teams_path = st_path / "teams"
    create_dir(teams_path)

    # Get no of teams
    teams = req(session, "get", "/api/v1/scoreboard").json()["data"]
    no_of_teams = len(teams)
    print("Found %s teams" % no_of_teams)

    print("Grabbing team scores...")
    with open(st_path / "scoreboard.txt", "a+") as f:
        sb = req(session, "get", "/api/v1/scoreboard").json()["data"]
        print("%-*s %-*s %-*s %-*s %-*s" %
              (8, "No.", 18, "Name", 5, "Score", 5, "Members", 5, "Solves"))
        for i in range(0, len(sb)):
            team_position = sb[i]["pos"]
            team_name = sb[i]["name"]
            team_score = sb[i]["score"]
            team_members = len(sb[i]["members"])
            no_of_solves = len(req(session, "get", "/api/v1/teams/" +
                                   str(sb[i]["account_id"]) + "/solves").json()["data"])

            f.write(("#%-*s %-*s %-*s %-*s %-*s\n" %
                     (5, team_position, 20, team_name, 5, team_score, 5, team_members, 5, no_of_solves)))
            print("#%-*s\t%-*s %-*s %-*s %-*s" %
                  (5, team_position, 20, team_name, 5, team_score, 5, team_members, 5, no_of_solves))

    print("Taking a screenshot of the current scoreboard...")
    # Grab screenshot of scoreboard
    screenshot("/scoreboard", str(st_path / "scoreboard.png"))

    print("Taking a screenshot of the current challenges page...")
    # Grab screenshot of scoreboard
    screenshot("/challenges", str(st_path / "challenges.png"))
    
    print("Taking a screenshot of team pages...")
    for i in range(0, no_of_teams):
        print(str(teams[i]["account_id"]))
        teams_page = req(session, "get", "/teams/" +
                         str(teams[i]["account_id"])).content
        soup = BeautifulSoup(teams_page, "html.parser")
        team_name = soup.find("h1", id="team-id").string
        # Grab screenshot of team page
        screenshot("/teams/" + str(teams[i]["account_id"]), str(teams_path) +
                   "/" + team_name + ".png")

    session.close()
    print("Done!")


def show_scores(session):
    print("Showing scores...")
    print("Press Ctrl + C to stop")

    # Get no of teams
    teams = req(session, "get", "/api/v1/teams").json()["data"]
    no_of_teams = len(teams)
    print("Found %s teams" % no_of_teams)

    myteam = req(session, "get", "/team")
    soup = BeautifulSoup(myteam.content, "html.parser")
    myteam_name = soup.find("h1", id="team-id").string

    while True:
        try:
            os.system('clear')
            sb = req(session, "get", "/api/v1/scoreboard").json()["data"]
            print("%-*s %-*s %-*s %-*s %-*s" %
                  (8, "No.", 18, "Name", 5, "Score", 5, "Members", 5, "Solves"))
            for i in range(0, len(sb)):
                team_position = sb[i]["pos"]
                team_name = sb[i]["name"]
                team_score = sb[i]["score"]
                team_members = len(sb[i]["members"])
                no_of_solves = len(req(session, "get", "/api/v1/teams/" +
                                       str(sb[i]["account_id"]) + "/solves").json()["data"])

                if myteam_name == team_name:
                    no_of_solves = str(no_of_solves) + "  <===="

                print("#%-*s\t%-*s %-*s %-*s %-*s" %
                      (5, team_position, 20, team_name, 5, team_score, 5, team_members, 5, no_of_solves))
            time.sleep(10)
        except KeyboardInterrupt:
            print("Done!")
            session.close()
            exit()


def check_solves(session):
    print("Checking solves per challenges...")
    print("Press Ctrl + C to stop")

    while True:
        try:
            os.system('clear')
            challenges_g = req(session, "get", "/api/v1/challenges")
            challenges = challenges_g.json()["data"]

            print("Found %s challenges" % len(challenges))
            print("Solves\t\tCategory\t\tName")
            for v in challenges:
                name = v["name"]
                category = v["category"]
                solves = req(session, "get", "/api/v1/challenges/" +
                             str(v["id"]) + "/solves").json()["data"]
                print("%s\t\t%s\t\t%s" % (len(solves), category, name))
            time.sleep(20)
        except KeyboardInterrupt:
            print("Done!")
            session.close()
            exit()


def setup(path):
    create_dir(path)
    print("CTF Folder created!")
    if (not os.path.exists(path / "readme.md")):
        open(path / "readme.md", 'a').close()
    os.system('git init ' + str(path))
    exit()


def create_challenge(path, session, challenge):
    category = challenge["category"]
    category_path = path / rep(category)
    create_dir(category_path)

    name = challenge["name"]
    points = challenge["value"]
    challenge_name = str(points) + "_" + rep(name)
    challenge_path = category_path / challenge_name
    create_dir(challenge_path)

    id = str(challenge["id"])
    if (not os.path.exists(challenge_path / "id")):
        with open(challenge_path / "id", "w") as f:
            f.write(str(id))

    description = str(
        challenge["description"].strip().encode("utf-8"), 'utf-8')
    if (not os.path.exists(challenge_path / "readme.md")):
        with open(challenge_path / "readme.md", "w") as f:
            f.write('Name: %s \n' % name)
            f.write('Points: %s \n\n' % points)
            f.write('Description:\n%s \n\n' % description)
            f.write('Solution:\n')

    if (not os.path.exists(challenge_path / "flag")):
        open(challenge_path / "flag", 'a').close()

    files = challenge["files"]
    if (len(files) > 0):
        for i in files:
            fname = i.split("/")[3].split("?")[0]
            if (not os.path.exists(challenge_path / rep(fname))):
                d = req(session, "get", i)
                with open(challenge_path / rep(fname), 'wb') as f:
                    f.write(d.content)


def create_dir(path):
    try:
        if (not os.path.exists(path)):
            os.mkdir(path)
            print("%s created" % path)
    except OSError:
        print("Error creating %s" % path)


def req(session, method, url, d=None, j=None):

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
    headers = {'User-Agent': user_agent}

    # http_proxy = "http://127.0.0.1:8080"
    # https_proxy = "https://127.0.0.1:8080"
    # proxyDict = {"http": http_proxy,"https": https_proxy}

    if method == 'get':
        return session.get(base_url + url, allow_redirects=True, verify=False, headers=headers)
    if method == 'post':
        # , proxies=proxyDict)
        return session.post(base_url + url, data=d, json=j, verify=False, headers=headers)
    if method == 'jpost':
        headers = {'User-Agent': user_agent, 'CSRF-Token': csrf_token(session, base_url),
                   'Content-Type': 'application/json', 'Accept': 'application/json'}
        return session.post(base_url + url, data=d, json=j, verify=False, headers=headers)


def rep(string):
    badchars = [' ', '<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for i in badchars:
        string = string.replace(i, "_")
    return string


def find_files(name, path):
    result = []
    for root, dirs, files in os.walk(path):
        if name in files:
            result.append(os.path.join(root, name))
    return result


def find_ctf_dir(ctf_name):
    if ctf_name in os.getcwd():
        dirs = os.getcwd().split("/")
        for i, v in enumerate(dirs):
            if v == ctf_name:
                ctf_dir = ''
                for x in range(i + 1):
                    if dirs[x] != '':
                        ctf_dir = ctf_dir + "/" + dirs[x]
                return ctf_dir
    print("Please run in the CTF directory otherwise run setup first!")
    exit()


def csrf_token(session, base_url):
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
    headers = {'User-Agent': user_agent}
    return nonce_pattern.findall(session.get(base_url, verify=False, headers=headers).text)[0]


def screenshot(url, filename):
    firefox_options = webdriver.FirefoxOptions()
    firefox_options.set_headless()
    firefox_driver = webdriver.Firefox(
        executable_path="/home/bored/bin/geckodriver", firefox_options=firefox_options, log_path='/tmp/geckodriver.log')

    firefox_driver.get(base_url)
    firefox_driver.delete_all_cookies()
    name, value = s.cookies.items()[0]
    cookie = {'name': name, 'value': value}
    firefox_driver.add_cookie(cookie)

    firefox_driver.get(base_url + url)

    time.sleep(1)
    firefox_elem = firefox_driver.find_element_by_tag_name('html')
    firefox_elem.screenshot(filename)
    firefox_driver.quit()


if __name__ == "__main__":
    try:
        base_url = sys.argv[1]
        username = sys.argv[2]
        action = sys.argv[3]
        ctf_name = base_url.replace("https://", "").replace(".", "_")

        if action == 'setup':
            path = os.getcwd()
            ctf_path = Path(path + "/" + ctf_name)
            setup(ctf_path)

        password = getpass()
        s = requests.Session()

        ctf_dir = find_ctf_dir(ctf_name)
        ctf_path = Path(ctf_dir)
        login(s, base_url, username, password)

        if action == 'challs':
            grab_challenges(ctf_path, s)
        if action == 'submit':
            submit_flags(ctf_path, s)
        if action == 'scores':
            grab_scores(ctf_path, s)
        if action == 'sscores':
            show_scores(s)
        if action == 'solves':
            check_solves(s)
    except(KeyboardInterrupt):
        print("\nExiting...")
        exit()
