The dotfiles of Karl M. Davis
=============================

This repo contains my dotfiles: the configuration/settings files used on the systems I login to.
I manage these files using [chezmoi](https://www.chezmoi.io/).

On a new system, run the following to install and initialize this whole setup:

    $ brew install chezmoi
    $ chezmoi init karlmdavis

That will automatically find and clone this `karlmdavis/dotfiles` repository from GitHub
  to `~/.local/share/chezmoi/` on the local system.

To push out the files in this repo to your home directory as dotfiles, run:

    $ chezmoi status
    $ chezmoi diff
    $ chezmoi apply

To manage a new file with chezmoi, run:

    $ chezmoi add <FILE>

Please note: chezmoi supports templating of files using Golang templates.
Do not edit a templated file directly, unless you want to deal with merging your changes later.
Instead, run this:

    $ chezmoi edit <FILE>

I've set chezmoi to automatically commit and push any changes to its managed files.
There's obviously a surprise vs. consistency tradeoff there, but I think it's the safer move.
See `[.chezmoi.toml.tmpl](./.chezmoi.toml.tmpl)` to adjust that, if needed.

## License

This project is licensed under the [GNU General Public License, Version 3](./LICENSE).

