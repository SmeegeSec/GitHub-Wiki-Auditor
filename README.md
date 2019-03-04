# GitHub Wiki Auditor

Read the full blog post "Auditing GitHub Repo Wikis for Fun and Profit" [here](https://********/).

### Description

The issue here is that most developers and engineers at large companies don't know this somewhat hidden setting exists. This results in wiki pages which anyone with a GitHub account can modify. So is this really a security issue? Yes...if allowing anyone to edit the wiki pages was **unintentional**. So why does this occur? I've typically found one of the main causes is engineers open sourcing a project, changing the repository from private to public. The enabled wiki setting stays the same, allowing anyone, not just collaborators, to edit the wiki page. It's also worth noting it's hard for repo owners to know when changes are made to their wiki pages because they don't get notified when it occurs and notifications can't be inherently configured.

### The Impact

The impact of this is pretty straightforward. Any GitHub user, even without being a collaborator or having any association with the account, can create or edit wiki pages. On these pages they could include hyperlinks, images, and more using [markdown](https://guides.github.com/pdfs/markdown-cheatsheet-online.pdf). It would be fairly easy to create a simple wiki page to social engineer people to install malicious libraries or navigate them to a malicious page owned by the attacker.

Another aspect to the impact of this issue is reputational damage. It's very easy to automate the editing of these wiki pages and would allow a nefarious actor to quickly add text and imagery which does not conform to the companies' principles.

### The Fix

Unfortunately for large companies with a lot of public repos, there doesn't appear to be an account-level setting which can manage all repository wiki settings. This means they have to control this on a per-repo basis with the "Restrict editing to collaborators only" setting (see, [Changing access permissions for wikis](https://help.github.com/en/articles/changing-access-permissions-for-wikis)). 

Other solutions could include:
* [Disable the wiki altogether](https://help.github.com/en/articles/disabling-wikis), if you don't need it.
* Engineer education about this issue and the related wiki settings.
* Periodically auditing your account's repositories with my script github-wiki-auditor.py.
* Create a plugin or service which notifies you have changes to your wiki pages.

### The Script

I wrote github-wiki-auditor.py which iterates over a list of GitHub accounts, and for each account, iterates through each repository. For each repository it checks if the wiki page is enabled, and if so, will send a request to create a new page. If the request is successful the user is notified and the next repository is checked. This script never actually modifies the wiki pages because the ability to edit can be confirmed without doing so.

Usage:
```
github-wiki-auditor.py [-h] --accounts_file ACCOUNTS_FILE [--output_file OUTPUT_FILE] [--username USERNAME]
[--password PASSWORD]

```