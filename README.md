## gitlab-webhook-branch-deployer

Clones and maintains directories with the latest contents of a branch.

### Usage

##### gitlab-webhook.ini

```$ ./gitlab-webhook.py```

##### Run the listening script:

```
[SYSTEM_CONFIGURATION]
WebhookHost	= example.com
WebhookPort	= 8040

[testproject]
Repository	= git@mygitlabdomain.com:user/testproject.git
BranchName	= dev
BranchDir	= /path/to/testproject/folder

[greatproject]
Repository	= git@mygitlabdomain.com:user/testproject.git
BranchName	= master
BranchDir	= /path/to/greatproject/folder
```

This will run the process and listen on port 8040 for POST requests from Gitlab that correspond to the two configs.

It will ignore any branch with a '/' in it's name. This is intentional, to allow for feature branches or similar that will not be cloned.

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
