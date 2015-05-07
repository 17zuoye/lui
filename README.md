lui [![Build Status](https://img.shields.io/travis/17zuoye/lui/master.svg?style=flat)](https://travis-ci.org/17zuoye/lui)
========================
A simple deployment setup tool, inspired by luigi and homebrew.


Usage
----------------------------
```bash
wget https://raw.githubusercontent.com/17zuoye/lui/master/lui.py -O lui
chmod +x lui
mv -f lui /usr/local/bin/
lui
```

Related to [luigi](http://github.com/spotify/luigi)
------------------------
As the luigi README said, "Luigi is a Python module that helps you build
complex pipelines of batch jobs. It handles dependency resolution,
workflow management, visualization etc.", dependencies install is
awesome!

Related to [homebrew](http://http://brew.sh/)
------------------------
Homebrew is a package manager for OS X, and there's also a fork version
called [linuxbrew](https://github.com/Homebrew/linuxbrew). They are both
written in Ruby, and `lui` want to directly use their package
informations, so `lui` need to be written in Ruby too, but now it is
still written in Python ...
