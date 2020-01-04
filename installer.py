import argparse
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--zsh", help="install zsh completions", action="store_true")
args = parser.parse_args()

# logo shit
print("\n********************************************************************************\n")
print("""\
\033[1;32m::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:'\033[1;34m##\033[1;32m:::'\033[1;34m##\033[1;32m:::::::'\033[1;34m###\033[1;32m:::::::'\033[1;34m########\033[1;32m::::'\033[1;34m########\033[1;32m::::'\033[1;34m####\033[1;32m:
: \033[1;34m##\033[1;32m::'\033[1;34m##\033[1;32m:::::::'\033[1;34m## ##\033[1;32m::::::... \033[1;34m##\033[1;32m..:::::... \033[1;34m##\033[1;32m..:::::. \033[1;34m##\033[1;32m::
: \033[1;34m##\033[1;32m:'\033[1;34m##\033[1;32m:::::::'\033[1;34m##\033[1;32m:. \033[1;34m##\033[1;32m:::::::: \033[1;34m##\033[1;32m:::::::::: \033[1;34m##\033[1;32m:::::::: \033[1;34m##\033[1;32m::
: \033[1;34m#####\033[1;32m:::::::'\033[1;34m##\033[1;32m:::. \033[1;34m##\033[1;32m::::::: \033[1;34m##\033[1;32m:::::::::: \033[1;34m##\033[1;32m:::::::: \033[1;34m##\033[1;32m::
: \033[1;34m##\033[1;32m. \033[1;34m##\033[1;32m:::::: \033[1;34m#########\033[1;32m::::::: \033[1;34m##\033[1;32m:::::::::: \033[1;34m##\033[1;32m:::::::: \033[1;34m##\033[1;32m::
: \033[1;34m##\033[1;32m:. \033[1;34m##\033[1;32m::::: \033[1;34m##\033[1;32m.... \033[1;34m##\033[1;32m::::::: \033[1;34m##\033[1;32m:::::::::: \033[1;34m##\033[1;32m:::::::: \033[1;34m##\033[1;32m::
: \033[1;34m##\033[1;32m::. \033[1;34m##\033[1;32m:::: \033[1;34m##\033[1;32m:::: \033[1;34m##\033[1;32m::::::: \033[1;34m##\033[1;32m:::::::::: \033[1;34m##\033[1;32m:::::::'\033[1;34m####\033[1;32m:
:.::::..:::::..:::::..::::::::..:::::::::::..::::::::....:::\033[0m\n\
""")

# own the necessary directory
user = os.popen("echo $USER").read().strip()
os.system("sudo chown -R %s /usr/local/bin" % user)
os.system("sudo chown -R %s /usr/local/etc" % user)
os.system("sudo chown -R %s /usr/local/opt" % user)

# installer
print("\033[1;34m=> \033[1;32mMaking katti directory in /usr/local/opt...\033[0m")
os.system("mkdir -v /usr/local/opt/katti")
print("\033[1;34m=> \033[1;32mMoving files to /usr/local/opt/katti...\033[0m")
os.system("cp -v katti.py /usr/local/opt/katti")
print("\033[1;34m=> \033[1;32mMaking katti shell script in /usr/local/bin...\033[0m")
print("echo 'python3 /usr/local/opt/katti/katti.py \"$@\"' > /usr/local/bin/katti")
os.system("echo 'python3 /usr/local/opt/katti/katti.py \"$@\"' > /usr/local/bin/katti")
print("chmod +x /usr/local/bin/katti")
os.system("chmod +x /usr/local/bin/katti")
print("\033[1;34m=> \033[1;32mMaking katti config directory in /usr/local/etc...\033[0m")
os.system("mkdir -v /usr/local/etc/katti")
print("\033[1;34m=> \033[1;32mMoving katti config files to /usr/local/etc/katti...\033[0m")
os.system("cp -v problem_ids.json /usr/local/etc/katti")
print("\033[1;34m=> \033[1;32mInstalling requirements...\033[0m")
os.system("python3 -m pip install --user -r requirements.txt")

# zsh completions installer
if args.zsh:
  print("\033[1;34m=> \033[1;32mMaking ZSH completions directory in $HOME/.zsh-completions...\033[0m")
  os.system("mkdir -vp $HOME/.config/zsh/custom_completions")
  print("\033[1;34m=> \033[1;32mMoving ZSH compdef files to $HOME/.zsh-completions...\033[0m")
  os.system("cp -v _katti $HOME/.config/zsh/custom_completions")
  print("\033[1;34m=> \033[1;32mEnsuring $HOME/.config/zsh/custom_completions is included in $fpath environment variable...\033[0m")
  print("echo 'fpath=($HOME/.config/zsh/custom_completions $fpath)' >> $HOME/.zshrc")
  os.system("echo 'fpath=($HOME/.config/zsh/custom_completions $fpath)' >> $HOME/.zshrc")
  print("autoload -U compinit && compinit' >> $HOME/.zshrc")
  os.system("echo 'autoload -U compinit && compinit' >> $HOME/.zshrc")
  print("\033[1;34m=> \033[1;32mRestarting shell session...\033[0m")
  os.system("exec zsh")
