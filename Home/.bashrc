#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
PS1='[\u@\h \W]\$ '

export JAVA_HOME=/usr/bin/java
export PATH=$JAVA_HOME/bin:$PATH

. "/home/ahmed/.deno/env"export STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

[[ "$TERM_PROGRAM" == "vscode" ]] && . "/home/ahmed/Downloads/ShipdSWE/VSCode-linux-x64/VSCode-linux-x64/resources/app/out/vs/workbench/contrib/terminal/common/scripts/shellIntegration-bash.sh"


