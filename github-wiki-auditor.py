import argparse
import json
import os
import requests
import ssl
import sys
import time
from lxml import cssselect, html  #pip install lxml, pip install cssselect

def main():
  parser = argparse.ArgumentParser(description='Find world-editable GitHub repository wikis.')
  parser.add_argument('--accounts_file', type=str, required=True, help='Newline separated file of GitHub accounts to scan')
  parser.add_argument('--username', type=str, help='GitHub username used for authentication. Required via argument or hardcoded.')
  parser.add_argument('--password', type=str, help='GitHub password used for authentication. Required via argument or hardcoded.')
  parser.add_argument("--output_file", type=str, help="Output file to write results to")
  parser.set_defaults(username = "")
  parser.set_defaults(password = "")
  parser.set_defaults(output_file = "")
  args = parser.parse_args()

  if args.username:
    gitHubUsername = args.username
  else:
    gitHubUsername = "YOUR HARDCODED USERNAME HERE"

  if args.password:
    gitHubPassword = args.password
  else:
    gitHubPassword = "YOUR HARDCODED PASSWORD HERE"

  accountsFile = args.accounts_file

  if os.path.isfile(accountsFile):
    editableWikiList = list()
  else:
    print "[*] Exiting - {0} is not a valid accounts input file.".format(accountsFile)
    sys.exit(1)
  
  if args.output_file:
    outputFile = open(args.output_file, "w")
  else:
    outputFile = ""

  with open(accountsFile) as accountsFileOpen:
    accountsList = accountsFileOpen.read().splitlines()
    
    # Create an authenticated session which will be used to attempt repo wiki requests. 
    # This user should not be a collaborator on any accounts' repos to avoid false positives.
    try:
      gitHubSession = requests.Session()
      gitHubLogin = gitHubSession.get("https://www.github.com/login")
      loginTree = html.fromstring(gitHubLogin.content)
      loginData = {i.get("name"):i.get("value") for i in loginTree.cssselect("input")}
      loginData["login"] = gitHubUsername
      loginData["password"] = gitHubPassword
      loginResponse = gitHubSession.post("https://github.com/session", data=loginData)
      if "Incorrect username or password" in loginResponse.text:
        print "Your GitHub username/password is incorrect!"
        sys.exit(1)
    except Exception as sessionError:
      print "[*] Exiting - there was an issue authenticating to GitHub using the provided credentials\n"
      print "[*] {0}".format(sessionError)
      sys.exit(1)

    accountCount = 0
    accountTotal = len(accountsList)
    rateLimitRequest = gitHubSession.get("https://api.github.com/rate_limit")
    rateLimit = json.loads(rateLimitRequest.content)["rate"]["remaining"]
    rateLimit429 = dict()
    
    if accountTotal > rateLimit:
      print "\nWARNING - GitHub limits the number of requests you can make within a period of time. Your current limit is {0} requests but you are scanning {1} accounts.".format(rateLimit, accountTotal)
    else:
      print "\nYour current GitHub request rate limit (number of accounts you can check): {0}".format(rateLimit)

    # Iterate through every account, and all repos in the account which have a wiki enabled.
    # A request to create a new wiki page will be made but no actual pages will be created.
    for account in accountsList:
      accountCount += 1

      # Use GitHub API to get list of account repositories. Depending on rate limit restrictions, this may eventually throw an error.
      try:
        repoRequest = gitHubSession.get("https://api.github.com/users/{0}/repos?per_page=100&page=1".format(account))
        repoJSON = json.loads(repoRequest.content)

        # Itereate through multiple pages to ensure all repo wikis are checked.
        while repoRequest:
          if "next" in repoRequest.links.keys():
            repoRequest = gitHubSession.get(repoRequest.links["next"]["url"])
            repoJSON.extend(json.loads(repoRequest.content))
          else:
            break
      except Exception as e:
        rateLimitRequest = gitHubSession.get("https://api.github.com/rate_limit")
        rateLimit = json.loads(rateLimitRequest.content)["rate"]["remaining"]
        
        if rateLimit < 2:
          print "\nYour current GitHub request rate limit (number of accounts you can check): {0}".format(rateLimit)
          print "Please wait until GitHub allows you to continue making requests."
          sys.exit(1)
        else:
          print "\nWARNING - Unexpected Error! Potential rate limit reached!\n"
          print "{0}".format(e)
      
      repoTotal = len(repoJSON)
      print "\n[*] Found {0} repositories for account {1}\n".format(repoTotal, account)

      if outputFile:
        outputFile.write("\n[*] Found {0} repositories for account {1}\n\n".format(repoTotal, account))
      
      for repoNum in range(repoTotal):
        try:
          repoFullName = repoJSON[repoNum]["full_name"]
        except Exception as error:
          if rateLimit == 0:
            print "\nYour current GitHub request rate limit (number of accounts you can check): {0}".format(rateLimit)
            print "Please wait until GitHub allows you to continue making requests.\n"
            sys.exit(1)
          else:
            if rateLimit429:
              print "\nThe following {0} accounts and repos were blocked by a rate limit (429 response) and should be checked manually:".format(len(rateLimit429))
              for uncheckedAccount in rateLimit429.iterkeys():
                print uncheckedAccount

              if outputFile:
                outputFile.write("\nThe following {0} accounts and repos were blocked by a rate limit (429 response) and should be checked manually:\n".format(len(rateLimit429)))
                for uncheckedAccount in rateLimit429.iterkeys():
                  outputFile.write("{0}\n".format(uncheckedAccount))

            print "\nWARNING - Unexpected Error! Potential rate limit reached!\n{0}".format(error)
            sys.exit(1)
          
        print "[*][Account {0}/{1}][Repo {2}/{3}] SCANNING wiki for {4}".format(accountCount, accountTotal, repoNum+1, repoTotal, repoFullName)

        if outputFile:
          outputFile.write("[*][Account {0}/{1}][Repo {2}/{3}] SCANNING wiki for {4}\n".format(accountCount, accountTotal, repoNum+1, repoTotal, repoFullName))
        
        if repoJSON[repoNum]["has_wiki"]:
          gitHubWikiResponse = gitHubSession.get("https://github.com/{0}/wiki/_new".format(repoFullName))
              
          # Archived repositories by the owner become read-only and respond with a 403
          # Occassionally a 429 Too Many Requests response will be returned and could cause inaccurate results
          if gitHubWikiResponse.status_code == 429:
            print "\n[*] 429 Too Many Requests response received - sleeping 15 seconds.\n"
            if outputFile:
              outputFile.write("\n[*] 429 Too Many Requests response received - sleeping 15 seconds.\n")
              
            # Sleep 15 seconds if we receive a "429 Too Many Requests" response which contains a "Retry-After: 120" header. 15 seconds is arbitrary but seems to work in most cases and won't occur often.
            time.sleep(15)
            gitHubWikiResponse = gitHubSession.get("https://github.com/{0}/wiki/_new".format(repoFullName))
              
            # Check for a second time to determine if sleep worked and if it did not add it to a dictionary to display to the user later. This is done because in my testing most of the time a 200 will follow but rarely a 429 again.
            if gitHubWikiResponse.status_code == 429:
              rateLimit429[repoFullName] = gitHubWikiResponse.status_code

          if gitHubWikiResponse.status_code == 200:
            wikiTree = html.fromstring(gitHubWikiResponse.content)
            wikiTitle = wikiTree.findtext(".//title")              
              
            if "Create New Page" in wikiTitle:
              editableWikiList.append(repoFullName)
              print "\tWorld Editable Wiki Found! - {0}".format(repoFullName)

              if outputFile:
                outputFile.write("\tWorld Editable Wiki Found! - {0}\n".format(repoFullName))

  # At this point all accounts have been checked.
  # If world editable wikis have been found, print them out in a newline separated list.
  if editableWikiList:
    editableWikiTotal = len(editableWikiList)
      
    if outputFile:
      outputFile.write("\nThe following {0} accounts and repos were found to have a world-editable wiki:\n".format(editableWikiTotal))
          
      for editableWiki in editableWikiList:
          outputFile.write("{0}\n".format(editableWiki))

    print "\nThe following {0} accounts and repos were found to have a world-editable wiki:".format(editableWikiTotal)
    editableWikiDict = dict()

    for editableWiki in editableWikiList:
      print editableWiki
    print

  # If accounts were not checked because they received a 429 Too Many Requests response they are listed here for the user to check manually.
  if rateLimit429:
    print "\nThe following {0} accounts and repos were blocked by a rate limit (429 response) and should be checked manually:".format(len(rateLimit429))
    for uncheckedAccount in rateLimit429.iterkeys():
      print uncheckedAccount

    if outputFile:
      outputFile.write("\nThe following {0} accounts and repos were blocked by a rate limit (429 response) and should be checked manually:\n".format(len(rateLimit429)))
      for uncheckedAccount in rateLimit429.iterkeys():
        outputFile.write("{0}\n".format(uncheckedAccount))

  if outputFile:
    outputFile.close()

if __name__ == "__main__":
  main()