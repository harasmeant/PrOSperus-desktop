# SPDX-License-Identifier: GPL-3.0-only
# Consola de PrOSperus en fish (lo mismo que /etc/profile.d/prosperus-shell.sh en bash):
# prompt en dos líneas (carpeta y rama; ❯ verde o rojo según la última orden), ls/cat con
# colores y fastfetch al abrir. fish ya colorea lo que se escribe y sugiere lo ya escrito.
status is-interactive; or return

set -g fish_greeting
function fish_prompt
    set -l last $status
    echo
    set_color --bold blue; echo -n (prompt_pwd --full-length-dirs 3)
    set_color magenta; echo (fish_git_prompt ' %s')
    test $last -eq 0; and set_color green; or set_color red
    echo -n '❯ '; set_color normal
end

if command -q eza
    alias ls 'eza --icons=auto --group-directories-first'
    alias ll 'eza -l --git --icons=auto --group-directories-first'
    alias tree 'eza --tree --icons=auto'
end
command -q bat; and alias cat 'bat --paging=never --style=plain'
# Una vez por consola: las fish o bash anidadas heredan la variable y no lo repiten.
if command -q fastfetch; and not set -q PROSPERUS_FETCH_SHOWN
    set -gx PROSPERUS_FETCH_SHOWN 1
    fastfetch
end
