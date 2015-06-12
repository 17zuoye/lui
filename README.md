lui [![Build Status](https://img.shields.io/travis/17zuoye/lui/master.svg?style=flat)](https://travis-ci.org/17zuoye/lui)
========================
A simple deployment setup tool, inspired by luigi and homebrew.


Usage
----------------------------
```bash
wget https://raw.githubusercontent.com/17zuoye/lui/master/lui.py
chmod +x lui.py
./lui.py


# install on clusters
for host in host1 host2
do
  echo
  echo "** Installing $host"
  export USE_USER=hadoop
  export lui=lui.py
  export json=lui_hadoop_cluster.json
  scp $lui $json root@$host:/tmp/ && ssh root@$host "su - $USE_USER -c '/tmp/$lui /tmp/$json;rm -f /tmp/$lui /tmp/$json; ' "
done

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


Run tests
----------------------------
```bash
pip install tox
tox
```
