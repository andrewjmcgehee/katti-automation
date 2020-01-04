import argparse
from bisect import bisect
import configparser
from datetime import datetime
import json
import multiprocessing as mp
import os
import random
import re
import sys
import time

# for customization of arg parser
class Parser(argparse.ArgumentParser):
  def _check_value(self, action, value):
    if action.choices is not None and value not in action.choices:
      raise argparse.ArgumentError(action, "invalid option")

# check python version
if sys.version_info[0] < 3:
  print("Python 3 required")
  print("Aborting...")
  sys.exit(0)

# set of dependencies
missing_dependencies = {
  "requests",
  "beautiful soup"
}

# import and catch dependency failures
try:
  import requests
  missing_dependencies.remove("requests")
  from bs4 import BeautifulSoup
  missing_dependencies.remove("beautiful soup")
except:
  for d in missing_dependencies:
    print("package \"%s\" required" % d)
  print("Aborting...")
  sys.exit(0)

# global verbose option
verbose = False

# supported programming languages
_suported_langs = {
  "cpp": ".cpp",
  "c++": ".cpp",
  "java": ".java",
  "python": ".py"
}
# convert an extension to a submission language
_extension_to_lang = {
  ".cpp": "C++",
  ".java": "Java",
  ".py": "Python"
}

# headers for submission
_HEADERS = { "User-Agent": "kattis-cli-submit" }

# URLs
_LOGIN_URL = "https://open.kattis.com/login"
_SUBMIT_URL = "https://open.kattis.com/submit"
_STATUS_URL = "https://open.kattis.com/submissions/"

# maximum number of times to check a submissions status
MAX_SUBMISSION_CHECKS = 60

# default size of submission history
DEFAULT_HIST_SIZE = 100

# user config files
user_conf = None
problems_conf = None
USER_CONF_PATH = "/usr/local/etc/katti/config.json"
PROBLEMS_CONF_PATH = "/usr/local/etc/katti/problem_ids.json"
HOME = os.path.expanduser('~')
ZSH_COMP_PATH = os.path.join(HOME, ".config/zsh/custom_completions/_katti")

# user conf or problems conf modified
modified = False

def update_zsh_completions():
  with open(ZSH_COMP_PATH, 'w') as f:
    f.write(
"""
#compdef katti

typeset -A opt_args

_arguments -C \
  '1: :->cmds' \
  '2: :->get_ids' \
  '*:: :->args' \
&& ret=0

case "$state" in
  (cmds)
    local commands
    commands=(
      "-h:show help"
      "--help:show help"
      "-g:get problem by id"
      "--get:get problem by id"
      "-r:run test cases on sample inputs"
      "--run:run test cases on sample inputs"
      "-p:submit solution to kattis"
      "--post:submit solution to kattis"
      "-v:set verbose"
      "--verbose:set verbose"
      "-d:display a problem's description in the default browser"
      "--description:display a problem's description in the default browser"
      "-b:set the default browser"
      "--default_browser:set the default browser"
      "--random:get a random problem with a given rating"
      "--stats:display solution stats"
      "--history:display submission history"
      "--history_size:set or query submission history size"
      "--update_period:set how frequently katti updates problem ratings in hours"
      "--update_zsh_completions:update katti completions for zsh users"
    )
    _describe -t commands "command" commands && ret=0
  ;;
  (get_ids)
    case $line[1] in
      (-g|--get)
        local ids
        ids=(
""")
    for k in sorted(problems_conf.keys()):
      f.write(' ' * 10 + "\"" + k + "\"\n")
    f.write(' ' * 8 + ')')
    f.write(
"""
        _describe -t ids "id" ids && ret=0
      ;;
    esac
  ;;
esac

return 1
""")

'''
Adds a problem id to problems conf file
'''
def add(problem_id):
  global problems_conf
  rating = get_problem_rating(problem_id)
  problems_conf[problem_id] = rating
  with open(PROBLEMS_CONF_PATH, 'w') as f:
    f.write(json.dumps(problems_conf))

"""
Gets the a problem's rating and sample inputs from kattis

Params: A string problem_id
Returns: None
"""
def get(problem_id):
  # get programming language and extension
  while True:
    language = input("Programming Language: ").lower()
    if language in _suported_langs:
      extension = _suported_langs[language]
      break
    print("Language \"%s\" not suported..." % language)
  # make GET call for problem rating
  rating = get_problem_rating(problem_id)
  # make GET call for samples zip file
  if verbose:
    print("Making http request: https://open.kattis.com/problems/" + problem_id + "/file/statement/samples.zip")
  r = requests.get("https://open.kattis.com/problems/" + problem_id + "/file/statement/samples.zip")
  # bad request
  if r.status_code != 200:
    print("URL <{}> returned non 200 status".format(r.url))
    print("Aborting...")
    sys.exit(0)
  # download and write zip file
  if verbose:
    print("Sample files found!")
    print("Downloading zip file...")
    print()
  with open("samples.zip", mode="wb") as f:
    f.write(r.content)
    f.close()
  # create the directory, unzip the samples, remove the zip file, create the boilerplate file
  if verbose:
    os.system("mkdir -v %s" % problem_id)
    print()
    os.system("unzip samples.zip -d %s" % problem_id)
    print()
    os.system("rm -iv samples.zip")
    print()
    print("Writing boilerplate files...")
    os.chdir(problem_id)
    write_boilerplate(problem_id, extension, rating)
    show_description()
    os.chdir("..")
  else:
    os.system("mkdir -p %s" % problem_id)
    os.system("unzip -q samples.zip -d %s" % problem_id)
    os.system("rm samples.zip")
    os.chdir(problem_id)
    write_boilerplate(problem_id, extension, rating)
    show_description()
    os.chdir("..")


"""
Helper function to get the current rating of problem from Kattis

Params: A string problem_id
Returns: A string representing the problem's rating
"""
def get_problem_rating(problem_id):
  r = requests.get("https://open.kattis.com/problems/" + problem_id)
  # bad request
  if r.status_code != 200:
    print("URL <{}> returned non 200 status".format(r.url))
    print("Aborting...")
    sys.exit(0)
  search = re.findall("Difficulty:[ </>a-z]*[0-9]\.[0-9]", r.text)[0]
  rating = search.split('>')[-1]
  return rating


"""
Opens a problem description in the default browser, either Chrome or Firefox

Params: None
Returns: None
"""
def show_description():
  problem_id = os.path.basename(os.getcwd())
  if problem_id not in problems_conf:
    print("Invalid problem ID: %s" % problem_id)
    print("Aborting...")
    sys.exit(0)
  if "default_browser" not in user_conf:
    set_default_browser()
  if input('Open in browser? (Y/N): ').lower() in {'y', 'yes'}:
    platform = sys.platform
    if platform == 'darwin':
      call = ""
      if user_conf["default_browser"] == "chrome":
        call = "open -a '/Applications/Google Chrome.app' 'https://open.kattis.com/problems/" + problem_id + "'"
      else:
        call = "open -a '/Applications/Firefox.app' 'https://open.kattis.com/problems/" + problem_id + "'"
      os.system(call)
    elif platform == 'linux':
      call = ""
      if user_conf["default_browser"] == "chrome":
        call = os.system("which google-chrome")
      else:
        call = os.system("which firefox")
      call += " 'https://open.kattis.com/problems/" + problem_id + "'"
      if call.startswith("/"):
        os.system(call)
      else:
        print("Unable to find valid binary for Chrome or Firefox")
        print("Aborting...")

"""
Sets the default web browser for displaying problem descriptions

Params: None
Returns: None
"""
def set_default_browser():
  global modified
  default = None
  while True:
    default = input("Set Chrome or Firefox as your default browser? ").lower()
    if default in {"firefox", "chrome"}:
      break
  user_conf["default_browser"] = default
  modified = True


"""
Opens and writes basic boilerplate to a file based on file type

Params: A string problem_id, a string extension, a string rating
Returns: None
"""
def write_boilerplate(problem_id, extension, rating):
  # c++ boilerplate
  if extension == ".cpp":
    content =\
"""\
/*
Rating: ~ %s / 10
Link: https://open.kattis.com/problems/%s
*/

#include <iostream>
#include <string>
#include <vector>
using namespace std;

typedef long long ll;

void fast() {
  ios_base::sync_with_stdio(false);
  cin.tie(NULL);
}

int main() {
  return 0;
}
""" % (rating, problem_id)

    with open(problem_id + extension, mode="w") as f:
      f.write(content)
      f.close()

  # java boilerplate
  elif extension == ".java":
    content =\
"""\
/*
Rating: ~ %s / 10
Link: https://open.kattis.com/problems/%s
*/

import java.io.*;
import java.util.*;

public class %s {
  static BufferedReader br = new BufferedReader(new InputStreamReader(System.in));

  public static void main(String[] args) {
  }
}
""" % (rating, problem_id, problem_id)

    with open(problem_id + extension, mode="w") as f:
      f.write(content)
      f.close()

  # python boilerplate
  elif extension == ".py":
    content =\
"""\
# Rating: ~ %s / 10
# Link: https://open.kattis.com/problems/%s

def main():

if __name__ == "__main__":
  main()
""" % (rating, problem_id)

    with open(problem_id + extension, mode="w") as f:
      f.write(content)
      f.close()


"""
Runs all the sample inputs for a given kattis problem and checks them for
basic correctness (does not check relative error)

Params: None
Returns: None
"""
def run():
  file_name = os.path.basename(os.getcwd())
  # find which language to use
  extension = get_source_extension(file_name)
  samples, answers = get_samples_and_answers()
  executable = run_compiler(file_name, extension)
  if executable is not None:
    if samples and answers:
      run_test_cases(executable, samples, answers)
    else:
      print("No sample inputs and answers found")
      print("Aborting...")


"""
Helper function to find a problem's sorce file extension

Params: A string problem_id
Returns: None
"""
def get_source_extension(problem_id):
  for f in os.listdir():
    base, extension = os.path.splitext(os.path.basename(f))
    if base == problem_id and extension in _extension_to_lang:
      return extension
  print("No suitable source files found")
  print("Currently Supported Extensions: \".cpp\", \".java\", \".py\"")
  print("Aborting...")


"""
Helper function to get sample inputs and outputs for comparison

Params: None
Returns: None
"""
def get_samples_and_answers():
  samples = []
  answers = []
  for f in os.listdir():
    base, extension = os.path.splitext(os.path.basename(f))
    if extension == ".in":
      samples.append(f)
    if extension == ".ans":
      answers.append(f)
  return (samples, answers)


"""
Helper function for run() method. Compiles the code for compiled languages and checks
existence of interpreter for interpreted languages

Params: A string file_name, a string extension
Returns: A string representing a system call to run the source code, or None on failure
"""
def run_compiler(file_name, extension):
  status = 1
  if extension == ".cpp":
    # check presence of g++ compiler
    status = os.system("which -s g++")
    if status != 0:
      print("Unable to locate g++ compiler")
      print("Aborting...")
      return None
    # compile the code
    if verbose:
      print("Compiling %s..." % (file_name + extension))
    os.system("g++ -std=c++11 %s" % (file_name + extension))
    return "./a.out"
  if extension == ".java":
    # check existence of javac compiler
    status = os.system("which -s javac")
    if status != 0:
      print("Unable to locate javac compiler")
      print("Aborting...")
      return None
    # compile the code
    if verbose:
      print("Compiling %s..." % (file_name + extension))
    os.system("javac %s" % (file_name + extension))
    return "java " + file_name
  if extension == ".py":
    if verbose:
      print("Trying to infer Python version...")
    version = determine_python_version(file_name + extension)
    python_warning = (
      "NOTE: Katti only uses the aliases 'python2' and 'python3' for python interpreters"
      + "\nPlease make sure the appropriate aliases are in your PATH environment variable"
      + "\nAborting..."
    )
    if version == 2:
      status = os.system("which -s python2")
      if status != 0:
        print("Unable to locate Python 2 interpreter")
        print(python_warning)
        return None
      return "python2 " + file_name + extension
    else:
      status = os.system("which -s python3")
      if status != 0:
        print("Unable to locate Python 3 interpreter")
        print(python_warning)
        return None
      return "python3 " + file_name + extension


"""
Runs a given kattis problem through the provided sample inputs - assumes
code is already compiled

Params: A command line string executable, a list of sample input files,
        a list of expected output files
Returns: None
"""
def run_test_cases(executable, sample_files, expected):
  print("Running test cases...")
  for i, sample in enumerate(sample_files):
    fail = False
    # get rid of .in extension in order to match with corresponding .ans file
    base = '.'.join(sample.split('.')[:-1])
    executable += " < " +  sample + " > test.out"
    os.system(executable)
    status = os.system("cmp test.out %s.ans" % base)
    if status != 0:
      if verbose:
        print("FAIL on sample input %s" % sample)
        print("<<< Expected Output >>>")
        with open(base + ".ans", mode="r") as f:
          print(f.read())
          f.close()
        print("<<< Actual Output >>>")
        with open("test.out", mode="r") as f:
          print(f.read())
          f.close()
      else:
        print("-", end="")
    else:
      if verbose:
        print("PASS on sample input: %s" % sample)
      else:
        print("+", end="")
  os.system("rm *.out 2>/dev/null")
  os.system("rm *.class 2>/dev/null")
  # formatting
  print()


"""
Scans a python file for tokens exclusive to python 2 to infer the python version

Params: A file name to scan
Returns: An integer version of python
"""
def determine_python_version(file_name):
  with open(file_name, mode="r") as f:
    for line in f:
      if "xrange" in line:
        if verbose:
          print("Found occurence of \"xrange\"")
          print("Python 2 inferred\n")
        return 2
      if "raw_input" in line:
        if verbose:
          print("Found occurence of \"raw_input\"")
          print("Python 2 inferred\n")
        return 2
    f.close()
  if verbose:
    print("No tokens exclusive to Python 2 found")
    print("Python 3 inferred\n")
  return 3


"""
Submits a problem to kattis

Params: None
Returns: None
"""
def post():
  config = get_config()
  problem_id = os.path.basename(os.getcwd())
  extension = get_source_extension(problem_id)
  lang = _extension_to_lang.get(extension)
  # only needed for Java submissions
  mainclass = problem_id if extension == ".java" else None
  # language to submit as
  if lang == "Python":
    version = determine_python_version(problem_id + extension)
    lang = "Python " + str(version)
  # list of files to submit
  submission_files = [problem_id + extension]
  try:
    login_response = login(config)
  except requests.exceptions.RequestException as e:
    print("Login Connection Failed:", e)
    sys.exit(0)
  report_login_status(login_response)
  confirm_submission(problem_id, lang, submission_files)
  # try post call
  try:
    submit_response = submit(
      login_response.cookies,
      problem_id,
      lang,
      submission_files,
      mainclass
    )
  except requests.exceptions.RequestException as e:
    print("Submit Connection Failed:", e)
    sys.exit(0)
  report_submission_status(submit_response)
  # print submission id message
  plain_text_response = submit_response.content.decode("utf-8").replace("<br />", "\n")
  print(plain_text_response)
  # check the submission acceptance status
  submission_id = plain_text_response.split()[-1].rstrip(".")
  check_submission_status(problem_id + extension, submission_id)


"""
Checks the status of a given submission for acceptance, TLE, etc.

Params: A string submission_file, a string submission_id
Returns: None
"""
def check_submission_status(submission_file, submission_id):
  global modified
  print("Awaiting result...\n")
  config = get_config()
  # login
  try:
    login_response = login(config)
  except requests.exceptions.RequestException as e:
    print("Login Connection Failed:", e)
    sys.exit(0)
  # limit number of http requests for a submissions status
  i = 0
  while i < MAX_SUBMISSION_CHECKS:
    response = requests.get(
      _STATUS_URL + submission_id,
      cookies=login_response.cookies,
      headers=_HEADERS
    )
    # parse html for accepted test cases
    soup = BeautifulSoup(response.content, "html.parser")
    status = soup.find("td", class_=re.compile("status"))
    if status:
      child = status.findChildren("span")[0]
      status = set(child["class"])
      runtime = soup.find("td", class_=re.compile("runtime"))
      # success
      if "accepted" in status:
        accepted = soup.find_all("span", class_=re.compile("accepted"))
        # limit length of output
        if len(accepted) > 47:
          print("Test Cases: "
                + ("+" * 47)
                + " plus "
                + str(len(accepted) - 47)
                + " more"
          )
        else:
          print("Test Cases: " + ("+" * len(accepted)))
        print("PASSED")
        print("Runtime: %s" % runtime.text)
        # insert problem into solved section of conf file in sorted order
        bin_search_index = bisect(user_conf["solved"], submission_file)
        if user_conf["solved"][bin_search_index-1] != submission_file:
          user_conf["solved"].insert(bin_search_index, submission_file)
        modified = True
        break
      # failure
      elif "rejected" in status:
        accepted = soup.find_all("span", class_=re.compile("accepted"))
        reason = soup.find("span", class_="rejected")
        cases = soup.find_all("span", title=re.compile("Test case"))
        num_cases = 0
        # find how many test cases passed and which one failed
        if cases:
          num_cases = cases[0]["title"]
          num_cases = re.findall("[0-9]+/[0-9]+", num_cases)
          num_cases = num_cases[0].split("/")[-1]
          # limit output length
          if len(accepted) > 46:
            print("Test Cases: " + ("+" * 44) + "...")
          else:
            print("Test Cases: " + ("+" * len(accepted)) + "-")
        print("FAILED")
        print("Reason:", reason.text)
        if num_cases == 0:
          print("Failed Test Case: N/A")
        else:
          print("Failed Test Case: %i/%s" % (len(accepted)+1, num_cases))
        print("Runtime: %s" % runtime.text)
        break
      # still running
      else:
        accepted = soup.find_all("span", class_=re.compile("accepted"))
        # update output
        if len(accepted) > 47:
          print("Test Cases: "
                + ("+" * 47)
                + " plus "
                + str(len(accepted) - 47)
                + " more", end='\r'
          )
        else:
          print("Test Cases: " + ("+" * len(accepted)), end='\r')
        time.sleep(0.5)
        i += 1
  # add to submission history
  dt = str(datetime.now()).split(".")[0]
  user_conf["history"].insert(0, dt + " " + submission_file)
  # truncate submission history to user config history size
  while len(user_conf["history"]) > user_conf["history_size"]:
    user_conf["history"].pop()
  modified = True


"""
Helper function to post a solution to kattis

Params: A requests cookies object for login, a string problem_id,
        a string lang, a list files, a string mainclass
Returns: A post request object
"""
def submit(cookies, problem_id, lang, files, mainclass=""):
  data = {
    "submit": "true",
    "submit_ctr": 2,
    "language": lang,
    "mainclass": mainclass,
    "problem": problem_id,
    "tag": "",
    "script": "true"
  }
  submission_files = []
  for i in files:
    with open(i) as f:
      submission_files.append(
        (
          "sub_file[]",
          (
            os.path.basename(i),
            f.read(),
            "application/octet-stream"
          )
        )
      )
  return requests.post(_SUBMIT_URL, data=data, files=submission_files, cookies=cookies, headers=_HEADERS)


"""
A confirmation message for submissions if verbose is set

Params: A string problem_id, a string lang, a list files
Returns: None
"""
def confirm_submission(problem_id, lang, files):
  if verbose:
    print("Problem:", problem_id)
    print("Language:", lang)
    print("Files:", ", ".join(files))
    print("Submit (Y/N): ", end="")
    if input()[0].lower() != "y":
      print("Aborting...")
      sys.exit(0)
    print()


"""
A status message for the login function

Params: A requests object response
Returns: None
"""
def report_login_status(response):
  status = response.status_code
  if status == 200 and verbose:
    print("Login Status: 200\n")
    return
  elif status != 200:
    print("Login Failed")
    if verbose:
      if status == 403:
        print("Invalid Username/Token (403)")
      elif status == 404:
        print("Invalid Login URL (404)")
      else:
        print("Status Code:", status)
    sys.exit(0)


"""
A status message for a problem submission

Params: A requests object response
Returns: None
"""
def report_submission_status(response):
  status = response.status_code
  if status == 200 and verbose:
    print("Submission Status: 200\n")
    return
  elif status != 200:
    print("Submit Failed")
    if verbose:
      if status == 403:
        print("Access Denied (403)")
      elif status == 404:
        print("Invalid Submission URL (404)")
      else:
        print("Status Code:", status)
    sys.exit(0)


"""
A helper function to load a users kattis rc file

Params: None
Returns: A ConfigParser object
"""
def get_config():
  config = configparser.ConfigParser()
  if not config.read([os.path.join(os.getenv("HOME"), ".kattisrc")]):
    print("Unable to locate .kattisrc file")
    print("Please navigate to https://open.kattis.com/help/submit to download a new one")
    print("Aborting...")
    sys.exit(0)
  return config


"""
A helper functiont to log a user in to kattis

Params: A ConfigParser object config
Returns: A requests object
"""
def login(config):
  username, token = parse_config(config)
  login_creds = {
    "user": username,
    "token": token,
    "script": "true"
  }
  return requests.post(_LOGIN_URL, data=login_creds, headers=_HEADERS)


"""
Helper function for login. Parses a config file for username and submit token.
On failure to parse config file, exits control flow

Params: A ConfigParser object
Returns: A tuple of username and token
"""
def parse_config(config):
  username = config.get("user", "username")
  token = None
  try:
    token = config.get("user", "token")
  except configparser.NoOptionError:
    pass
  if token is None:
    print("Corrupted .katisrc file")
    print("Please navigate to https://open.kattis.com/help/submit and download a new .kattisrc")
    print("Aborting...")
    sys.exit(0)
  return (username, token)


"""
A helper function to print a users submission stats

Params: None
Returns: None
"""
def get_stats():
  if len(user_conf["solved"]) == 0:
    print("You haven't solved any problems yet!")
    return
  solved = user_conf["solved"]
  # last updated
  prev_update = datetime.strptime(user_conf["ids_last_updated"], "%Y-%m-%d %H:%M:%S.%f")
  current = datetime.now()
  # 3600 seconds in hour - no hours field
  hours = (current - prev_update).total_seconds() / 3600
  if hours >= user_conf["ratings_update_period"]:
    get_updated_ratings()
  # temporary record for various stats tracked
  stats = {
    "cpp": {
      "freq": 0,
      "pr": (None, 0),
      "ratings": []
    },
    "java": {
      "freq": 0,
      "pr": (None, 0),
      "ratings": []
    },
    "py": {
      "freq": 0,
      "pr": (None, 0),
      "ratings": []
    }
  }
  for prob in solved:
    problem_id, ext = prob.split(".")
    if ext not in stats:
      continue
    stats[ext]["freq"] += 1
    stats[ext]["ratings"].append(problems_conf[problem_id])
    if problems_conf[problem_id] > stats[ext]["pr"][1]:
      stats[ext]["pr"] = (problem_id, problems_conf[problem_id])
  # for getting averages and personal bests (language specific)
  cpp_num, cpp_denom = sum(stats["cpp"]["ratings"]), len(stats["cpp"]["ratings"])
  java_num, java_denom = sum(stats["java"]["ratings"]), len(stats["java"]["ratings"])
  py_num, py_denom = sum(stats["py"]["ratings"]), len(stats["py"]["ratings"])
  cpp_avg, cpp_pr = cpp_num / cpp_denom, stats["cpp"]["pr"]
  java_avg, java_pr = java_num / java_denom, stats["java"]["pr"]
  py_avg, py_pr = py_num / py_denom, stats["py"]["pr"]
  # total stats
  total_num, total_denom = (cpp_num + java_num + py_num), (cpp_denom + java_denom + py_denom)
  avg, pr = total_num / total_denom, max(cpp_pr, java_pr, py_pr, key=lambda x: x[1])
  print()
  print("|  LANGUAGE  |   SOLVED   | AVG RATING |               PR               |")
  print("-------------------------------------------------------------------------")
  print("| C++        | %10i | %10.2f | %-26s %3.1f |" % (cpp_denom, cpp_avg, cpp_pr[0], cpp_pr[1]))
  print("| Java       | %10i | %10.2f | %-26s %3.1f |" % (java_denom, java_avg, java_pr[0], java_pr[1]))
  print("| Python     | %10i | %10.2f | %-26s %3.1f |" % (py_denom, py_avg, py_pr[0], py_pr[1]))
  print("-------------------------------------------------------------------------")
  print("| TOTAL      | %10i | %10.2f | %-26s %3.1f |" % (total_denom, avg, pr[0], pr[1]))


"""
Helper to get floating point problem rating rather than string

Params: A string problem_id
Returns: A float representing the rating
"""
def get_numeric_rating(problem_id):
  return float(get_problem_rating(problem_id))


"""
Gets up to date problem ratings with multiprocessed calls to kattis
"""
def get_updated_ratings():
  global modified
  # updated values
  user_conf["ids_last_updated"] = str(datetime.now())
  ordered_keys = list(problems_conf.keys())
  # can tinker with this value if needed
  pool = mp.Pool(processes=128)
  print("Getting up-to-date problem ratings...")
  for i, val in enumerate(pool.imap(get_numeric_rating, ordered_keys)):
    print("\rStatus: [" + "%-40s" % ("█" * int(40 * i / len(ordered_keys))) + "] %.1f%%" % (100 * i / len(ordered_keys)), end="")
    problems_conf[ordered_keys[i]] = val
  print("\rStatus: [%-40s" % ("█" * 40) + "] 100.0%")
  pool.close()
  pool.join()
  modified = True


"""
Displays uses submission history

Params: None
Returns: None
"""
def get_history():
  if len(user_conf["history"]) == 0:
    if user_conf["history_size"] == 0:
      print("You currently aren't tracking your submission history because your history size is 0")
    else:
      print("Your submission history is empty")
    return
  print()
  print(" #    | YYYY-MM-DD HH:MM:SS | SUBMISSION")
  print("-----------------------------------------------------")
  for i, submission in enumerate(user_conf["history"], 1):
    d, t, sub = submission.split(" ")
    print(" %-4i | %s %s | %-24s" % (i, d, t, sub))
  print()


"""
Sets a users submission history size

Params: An int size
Returns: None
"""
def set_history_size(size):
  global modified
  if size < user_conf["history_size"]:
    print("NOTE:")
    print("  - setting the history size is destructive")
    print("  - the history will immediately shrink from %i to %i" % (user_conf["history_size"], size))
    print("  - setting the history size to 0 effectively clears your history")
    print()
    ans = input("Do you wish to continue? (Y/N): ")
    if ans.lower() not in {"y", "yes"}:
      return
  user_conf["history_size"] = size
  while len(user_conf["history"]) > size:
    user_conf["history"].pop()
  modified = True


"""
Shows a users history size

Params: None
Returns: None
"""
def get_history_size():
  print(user_conf["history_size"])


"""
A helper functiont to validate history size, if -1 simply shows history size

Params: An int size
Returns: None
"""
def handle_history_size(size):
  arg_size = None
  try:
    arg_size = int(size)
    if arg_size < -1:
      raise ValueError
  except ValueError:
    print("Size must be a positive integer value or -1")
    print("Aborting...")
    sys.exit(0)
  if arg_size is not None:
    if arg_size == -1:
      get_history_size()
    else:
      set_history_size(arg_size)


"""
Gets a random kattis problem within a range, [rating, rating + 0.9]

Params: An int rating
Returns: None
"""
def get_random(rating):
  global modified
  invalid = False
  try:
    rating = int(rating)
  except:
    invalid = True
  if rating < 1 or rating >= 10 or invalid:
    print("Invalid rating. Rating must be a valid integer between 1 and 10")
    print("Aborting...")
    sys.exit(0)
  # update ratings if necessary
  prev_update = datetime.strptime(user_conf["ids_last_updated"], "%Y-%m-%d %H:%M:%S.%f")
  current = datetime.now()
  # 3600 seconds in hour - no hours field
  hours = (current - prev_update).total_seconds() / 3600
  if hours >= user_conf["ratings_update_period"]:
    get_updated_ratings()
  # will hold all unsolved problems within the range
  choices = set()
  solved = set([i.split(".")[0] for i in user_conf["solved"]])
  for problem, val in problems_conf.items():
    if val == rating:
      choices.add(problem)
  choices -= solved
  if choices:
    pick = random.choice(list(choices))
    print("Getting %s..." % pick)
    get(pick)
    return
  print("It appears you have solved all problems rated %.1f - %.1f" % (rating, rating + 0.9))


"""
Set how frequently ratings will be updated

Params: An int period
Returns: None
"""
def set_update_period(period):
  global user_conf, modified
  invalid = False
  try:
    period = int(period)
  except:
    invalid = True
  # max is one week
  if period < 1 or period > 7 * 24 or invalid:
    print("Invalid period. Must be a valid integer > 0 and <= 168 (one week)")
    print("Aborting...")
    sys.exit(0)
  user_conf["ratings_update_period"] = period
  modified = True


"""
Display the kattis usage message

Params: None
Returns: a string representing the usage message
"""
def usage_msg():
  return "katti [-g <problem-id>] [-r] [-p] [-h] [-v]"


def main():
  global verbose, user_conf, problems_conf
  # load or create conf files if they dont exist
  if os.path.exists(USER_CONF_PATH):
    user_conf = json.load(open(USER_CONF_PATH))
  else:
    user_conf = {
      "solved": [],
      "history": [],
      "history_size": DEFAULT_HIST_SIZE,
      "ids_last_updated": str(datetime.now()),
      "ratings_update_period": 72
    }
  # should have been downloaded with katti
  if os.path.exists(PROBLEMS_CONF_PATH):
    problems_conf = json.load(open(PROBLEMS_CONF_PATH))
  else:
    print("Your problem ids JSON file appears to be corrupted")
    print("Please download and install a new one at https://github.com/andrewjmcgehee/katti-automation")
    print("Aborting...")
    sys.exit(0)
  # add command line args
  arg_parser = Parser(usage=usage_msg())
  arg_parser.add_argument(
    "-g",
    "--get",
    metavar="<problem-id>",
    help="get a kattis problem by its problem id",
    type=str,
    choices=list(problems_conf.keys())
  )
  arg_parser.add_argument("-r", "--run", help="run the test cases for a given problem", action="store_true")
  arg_parser.add_argument("-p", "--post", help="submit a kattis problem", action="store_true")
  arg_parser.add_argument("-v", "--verbose", help="receive verbose outputs", action="store_true")
  arg_parser.add_argument("-d", "--description", help="display a problem's description in chrome", action="store_true")
  arg_parser.add_argument("-b", "--default_browser", help="set the default browser to show problem descriptions", action="store_true")
  arg_parser.add_argument("--add", metavar="<problem_id", help="add a problem id to your problem config file")
  arg_parser.add_argument("--random", metavar="<rating>", help="get a random kattis problem with a given rating")
  arg_parser.add_argument("--stats", help="get kattis stats if possible", action="store_true")
  arg_parser.add_argument("--history", help="see your 50 most recent kattis submissions", action="store_true")
  arg_parser.add_argument("--history_size", metavar="<size>", help="set history size with a number and query history size with -1")
  arg_parser.add_argument("--update_period", metavar="<hours>", help="set how frequently katti updates problem ratings in hours")
  arg_parser.add_argument("--update_zsh_completions", help="update katti completions for zsh users", action="store_true")
  args = arg_parser.parse_args()
  # track verbosity
  verbose = args.verbose
  # handle args passed in
  if args.get:
    get(args.get)
  elif args.random:
    get_random(args.random)
  elif args.run:
    run()
  elif args.post:
    post()
  elif args.add:
    add(args.add)
  elif args.default_browser:
    set_default_browser()
  elif args.description:
    show_description()
  elif args.stats:
    get_stats()
  elif args.history:
    get_history()
  elif args.history_size:
    handle_history_size(args.history_size)
  elif args.update_period:
    set_update_period(args.update_period)
  elif args.update_zsh_completions:
    update_zsh_completions()
  else:
    print("usage:", usage_msg())
  # update conf files if needed
  if modified:
    with open(USER_CONF_PATH, mode="w") as f:
      f.write(json.dumps(user_conf))
      f.close()
    with open(PROBLEMS_CONF_PATH, mode="w") as f:
      f.write(json.dumps(problems_conf))
      f.close()

if __name__ == "__main__":
  main()
