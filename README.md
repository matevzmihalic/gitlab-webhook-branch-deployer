## gitlab-webhook-branch-deployer

Clones and maintains directories with the latest contents of a branch.

### Usage

##### gitlab-webhook.ini

```$ ./gitlab-webhook.py```

##### Run the listening script:

```
[SYSTEM_CONFIGURATION]
WebhookHost	= localhost
WebhookPort	= 8040
GitlabIP	= 127.0.0.1
RailsPath	= false

[testproject]
Repository	= git@mygitlabdomain.com:user/testproject.git
BranchName	= master
BranchDir	= /path/to/master/branch/folder
SudoUser	= user
ShBefore	= /path/to/bash/script.sh
ShAfter		= /path/to/bash/script.sh

[testproject-dev-branch]
Repository	= git@mygitlabdomain.com:user/testproject.git
BranchName	= dev
BranchDir	= /path/to/dev/branch/folder
SudoUser	= user
ProjectId	= 1234
```

This will run the process and listen on port 8040 for POST requests from Gitlab that correspond to the two configs.

It will ignore any branch with a '/' in it's name. This is intentional, to allow for feature branches or similar that will not be cloned.

Git pull is running under SudoUser from config file and runs ShBefore script before pulling and ShAfter right after.

### Deployment

#####Create a webhook records in Gitlab for these configurations:

```
http://examle.com:8040/testproject
```

and

```
http://examle.com:8040/greatproject
```

### Acknowledgements

Inspired by https://github.com/shawn-sterling/gitlab-webhook-receiver.

### License

GPLv2
