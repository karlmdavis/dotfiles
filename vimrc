" Install vim-plug if it's not already present.
if empty(glob('~/.vim/autoload/plug.vim'))
  silent !curl -fLo ~/.vim/autoload/plug.vim --create-dirs
    \ https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
  autocmd VimEnter * PlugInstall --sync | source $MYVIMRC
endif

" Plugins to be managed via https://github.com/junegunn/vim-plug
" will be listed in this plug#begin / plug#end block.

" After updating this set, run `:so %` (in this buffer!) to reload your `.vimrc`
" and then either `:PlugInstall` or `:PlugUpdate` to install/update the entries.
call plug#begin('~/.vim/plugged')

" Set sensisble .vimrc defaults.
Plug 'tpope/vim-sensible'

" Provide session management.
Plug 'tpope/vim-obsession'

" Useful relative-vs.-absolute line number behavior.
Plug 'jeffkreeftmeijer/vim-numbertoggle'

" Install a decent Markdown mode.
Plug 'godlygeek/tabular' | Plug 'plasticboy/vim-markdown'

" Enable the Rust plugin, which includes autoformatting via rustfmt, syntax highlisting, and more.
Plug 'rust-lang/rust.vim'

" Provides a syntax checker that works with rust.vim and cargo.
Plug 'vim-syntastic/syntastic'

" Provides a file browser left-pane.
Plug 'scrooloose/nerdtree'

" Provides an outline view for Rust files (or anything supported by ctags).
" Note: ctags is a separate binary that must be installed outside of vim.
Plug 'majutsushi/tagbar'

" Provides auto-complete for Rust (or whatever). See repo for additional
" installation instructions (e.g. `cd ~/.vim/plugged/YouCompleteMe &&
" ./install.py --rust-completer`).
Plug 'Valloric/YouCompleteMe'

" Enable the vim-ansible-yaml plugin, which makes Ansible editing sane.
Plug 'chase/vim-ansible-yaml'

" Install a decent Python mode.
Plug 'python-mode/python-mode'

" Add plugins to &runtimepath
call plug#end()

" Relative line numbers (sort of, per vim-numbertoggle plugin).
set number relativenumber

" In markdown mode, convert tabs to spaces (press ctrl+v,tab to insert an
" actual tab when needed).
autocmd FileType markdown set expandtab

" Disable vim-markdown's folding (dumbest feature ever).
let g:vim_markdown_folding_disabled = 1

" Adjust how wide tab characters appear.
set tabstop=4

" Make tabs visible.
set list
set listchars=tab:␉·

" Automatically format Rust files on save.
let g:rustfmt_autosave = 1

" Configure NERDtree to start at launch.
autocmd VimEnter * NERDTree
autocmd BufEnter * NERDTreeMirror

" CTRL-t to toggle tree view with CTRL-t.
nmap <silent> <C-t> :NERDTreeToggle<CR>
" Set F2 to put the cursor to the nerdtree.
nmap <silent> <F2> :NERDTreeFind<CR>

" Press F8 to toggle tagbar's outline view.
nmap <F8> :TagbarToggle<CR>
