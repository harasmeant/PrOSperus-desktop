# SPDX-License-Identifier: GPL-3.0-only
# Consola de PrOSperus: prompt en dos líneas (carpeta y rama de git; ❯ verde o rojo según
# la última orden), ls/cat con colores (eza, bat) y fastfetch al abrir cada consola.
# Base escrita por qwen2.5-coder (local), revisada.
[ -n "$BASH_VERSION" ] || return 0
case $- in *i*) ;; *) return 0 ;; esac
# Fedora, Arch y Debian guardan git-prompt.sh en sitios distintos.
for f in /usr/share/git-core/contrib/completion/git-prompt.sh /usr/share/git/completion/git-prompt.sh \
         /usr/lib/git-core/git-sh-prompt; do
    [ -f "$f" ] && { . "$f"; GIT_PS1_SHOWDIRTYSTATE=1; break; }
done; unset f
__prosperus_prompt() {
    local status=$? colour=32
    [ "$status" -eq 0 ] || colour=31
    PS1='\n\[\e[1;34m\]\w\[\e[0m\]'
    if type __git_ps1 >/dev/null 2>&1; then
        PS1+="\[\e[35m\]$(__git_ps1 ' %s')\[\e[0m\]"
    fi
    PS1+="\n\[\e[${colour}m\]❯\[\e[0m\] "
}
PROMPT_COMMAND=__prosperus_prompt
if command -v eza >/dev/null 2>&1; then
    alias ls='eza --icons=auto --group-directories-first' ll='eza -l --git --icons=auto --group-directories-first' \
        tree='eza --tree --icons=auto'
fi
command -v bat >/dev/null 2>&1 && alias cat='bat --paging=never --style=plain'
# Una vez por consola: las bash anidadas heredan la variable y no lo repiten.
if command -v fastfetch >/dev/null 2>&1 && [ -z "$PROSPERUS_FETCH_SHOWN" ]; then
    export PROSPERUS_FETCH_SHOWN=1
    fastfetch
fi
true
