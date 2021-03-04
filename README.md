### Tool description
Obtrusive is a multiclient, multivictim DOS fleet for eth2 based on the prysm client.  
  
Features:
* establishes adverserial connections to up to [N] clients (any *sane* N)
* currently supports attacking Prysm, (Nimbus, Teku, Lighthouse)
* rate limit conform
* vpn support for rate limit circumvention

### Setup

##### Installation
First, clone the repo and move into directory:
```
git clone https://github.com/org404/obtrusive.git
cd obtrusive
```
Setup python virtual environment:
```
virtualenv -p python3.8 .venv
source .venv/bin/active
python -m pip install -r requirements.txt
```

##### Configuration
Use sample file from the repo:
```
cp sample-config.yml config.yml
```
Now, open the file with editor of your choice and fill your hetzner token.

##### Run
You already can run the script and see how it goes. For that run:
```
python -m obtrusive
```
When the execution finishes, you can open config file again and tweak some stuff or check what was executed.
But you should finish reading through readme first.

##### Remove servers
After execution we need to clean up the servers, so we don't get charged for them:
```
# Note: you can also use `--delete` flag
python -m obtrusive -d
```

##### Config options
**vars** namespace can contain any lists of items which can be used anywhere in the **commands** or **assertions** namespace with "use" keyword.  
  
**commands** namespace:
* *command*: a string which contains a command to be executed through terminal connection.
* *show*: a boolean which defined whether output of the command should be displayed on the screen.
* *use*: a name of "vars" list as a string that is used to get a value from a list with auto-incremented index. Will give an error on the config-parsing stage if list is too small (index out of range).
* *increment*: a boolean that is dependent on the "use" keyword; default is "true"; if increment is "false", auto-increment will be delayed, and you will get the same value as in previous command.
  
**assertions** namespace supports **commands**' keywords and additionally:
* *contains*: a string that must be in the output of the according command for assertion to pass.
  
*Important Note: any other keywords added in the config, that are not recognized as a special keywords, will be passed to the "format" function as a context vars. Which means you can easily isolate sensitive data from links or any other commands. For usage example see "sample-config.yml"*
