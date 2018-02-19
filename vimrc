" Plugins to be managed via https://github.com/junegunn/vim-plug
" will be listed in this plug#begin / plug#end block.
call plug#begin('~/.vim/plugged')

" Set sensisble .vimrc defaults.
Plug 'tpope/vim-sensible'

" Install a decent Markdown mode.
Plug 'godlygeek/tabular' | Plug 'plasticboy/vim-markdown'

" Enable the Rust plugin, which includes autoformatting via rustfmt, syntax highlisting, and more.
Plug 'rust-lang/rust.vim'

" Enable the vim-ansible-yaml plugin, which makes Ansible editing sane.
Plug 'chase/vim-ansible-yaml'

" Add plugins to &runtimepath
call plug#end()

" Automatically format Rust files on save.
let g:rustfmt_autosave = 1

" Disable vim-markdown's folding (dumbest feature ever).
let g:vim_markdown_folding_disabled = 1

" Adjust how wide tab characters appear.
set tabstop=4
