# -*-coding:utf-8-*-


"""
Packages with dependencies declared.

Features:
    1. Install dependencies detected.
    2. No repeated running.
    3. User role checked.
    4. Only standard python is depended.

TODO:
    1. support change user between envs.


Difference ways that executed shell in Python:
    1: os.system                   -> print shell executing output instantly.
    2. commands.getstatusoutput    -> no outputs, return status and output at the end of shell scripts executing.

"""

import os
import sys
import pwd
import commands as COMMANDS
import json

curr_dir = os.getcwd()


def get_current_user():
    return COMMANDS.getstatusoutput("whoami")[1]
source_profile = "source /etc/profile; source ~/.bashrc; source ~/.bash_profile;" if os.getenv("IS_NEED_SOURCE", "False") == "True" else ""


# TODO assert env is ready
# 1. whoami
# 2. yum, rpm

class Env(object):
    """ Package install env. """

    dry = False
    verbose = True

    user = NotImplemented
    users = NotImplemented

    # 1 requires
    def requires(self):
        """ return required env class. """
        return []

    # 2 install
    def run(self):
        raise NotImplementedError

    # 3 done
    def done(self):
        """ Check if current env is already setuped. """
        return False

    def home_path(self, path):
        return os.path.join(os.getenv("HOME"), path)

    def _users(self):
        _us = []
        if self.user is not NotImplemented:
            _us.append(self.user)
        if self.users is not NotImplemented:
            _us.extend(self.users)
        return _us


class PackageEnv(Env):

    def run(self):
        """ Run the install shell scripts"""
        # 1 build shell command list
        commands = ["%s %s" % (self.install_cmd(), pkg1) for pkg1 in self.packages()]

        for command1 in commands:
            print "[command]", command1
            # COMMANDS.getstatusoutput(command1)
            os.system(command1)  # has realtime shell outputs

    def run_cmd(self):
        " return a shell command str. "
        return ""

    def packages(self):
        """ return a str list. """
        return []


class YumEnv(PackageEnv):
    user = "root"

    def run_cmd(self):
        return "%s    yum -y install" % source_profile


class ShellBehavior(Env):

    def run(self):
        context = "\n".join([
            source_profile,
            self.shell_scripts(),
        ])
        os.system(context)

    def shell_scripts(self):
        raise NotImplementedError


class AddUserEnv(ShellBehavior):
    user = "root"
    custom_user = NotImplementedError

    @property
    def _user(self):
        _u = self.custom_user() if callable(self.custom_user) else self.custom_user
        assert isinstance(_u, basestring), _u
        return _u

    def done(self):
        try:
            pwd.getpwnam(self._user)
            return True
        except KeyError:
            return False

    def shell_scripts(self):
        return u"""
            export USERNAME=%s
            useradd -d /home/$USERNAME -s /bin/bash $USERNAME

            cd /home/$USERNAME
            mkdir -p .ssh
            touch .ssh/authorized_keys
            chmod 0600 .ssh/authorized_keys
            chmod -R 0600 .ssh
            chown -R $USERNAME:$USERNAME .ssh
        """ % self._user


class FixPython26to27(ShellBehavior):
    """ https://pypi.python.org/pypi/setuptools/0.9.8#unix-based-systems-including-mac-os-x """

    def done(self):
        is_valid = True
        try:
            import pkg_resources
        except:
            is_valid = False
        pkg_resources  # use it, cause PEP8 needed.
        return is_valid

    def shell_scripts(self):
        return " wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py -O - | python"


class PythonDepYumPackages(YumEnv):

    def requires(self):
        return [FixPython26to27]

    def done(self):
        done_list = COMMANDS.getstatusoutput("rpm -qa")[1]
        needed_rpm_packages = self.packages()
        is_all_done = True
        for rpm_package in needed_rpm_packages:
            if rpm_package not in done_list:
                print "[error] %s is not done." % rpm_package
                is_all_done = False
                break
        return is_all_done


class GitEnv(YumEnv):
    def packages(self):
        return "git"

    def done(self):
        return os.path.exists("/usr/bin/git")


class CommonYumPackages(YumEnv):
    # packages is copied from https://github.com/mvj3/install/blob/master/definitions/hadoop_centos/base.sh

    def done(self):
        commands = " ".join(self.packages()).strip().split(" ")
        is_yes = True
        for c1 in commands:
            output2 = COMMANDS.getstatusoutput("which %s" % c1)[1]
            if (" no " in output2) or (" not " in output2):  # both match Linux and OSX.
                is_yes = False
        return is_yes


class LuigiDepYumPackages(YumEnv):

    def requires(self):
        return [PythonDepYumPackages]

    def done(self):
        """ `rpm -qa` 返回的是一行一行软件包，但是没有空格符。"""
        done_list = COMMANDS.getstatusoutput("rpm -qa")[1]
        return ("mysql-devel" in done_list) and \
               ("\n" in done_list)

    def packages(self):
        return "mysql-devel " \
               " "


class PyenvEnv(ShellBehavior):

    def requires(self):
        return GitEnv

    def done(self):
        return os.path.exists(os.getenv("PYENV_ROOT"))

    def shell_scripts(self):
        return u"""
          cd $HOME
          git  clone https://github.com/yyuu/pyenv.git                  .pyenv
          echo ''                                                    >> .bash_profile
          echo 'export PIP_DOWNLOAD_CACHE=$HOME/.pip_download_cache' >> .bash_profile
          echo 'export PYENV_ROOT="$HOME/.pyenv"'                    >> .bash_profile
          echo 'export PATH="$PYENV_ROOT/bin:$PATH"'                 >> .bash_profile
          echo 'export PYENV_VERSION=2.7.9'                          >> .bash_profile
          echo 'eval "$(pyenv init -)"'                              >> .bash_profile
          """


class PyenvInstalPython279(ShellBehavior):

    def requires(self):
        return PyenvEnv

    def done(self):
        return os.path.exists(os.path.join(os.getenv("PYENV_ROOT"), "versions/2.7.9"))

    def shell_scripts(self):
        return u"""
          # http://fduo.org/pyenv-mirrow/
          export PYTHON_BUILD_MIRROR_URL="http://pyenv.qiniudn.com/pythons/"
          # CFLAGS="-I$(xcrun --show-sdk-path)/usr/include" # https://github.com/yyuu/pyenv/wiki/Common-build-problems # find the zlib headers
          pyenv install --keep --verbose 2.7.9
          pyenv shell 2.7.9
          pyenv rehash
          """


class PipEnv(PackageEnv):

    def requires(self):
        return PyenvInstalPython279

    def run_cmd(self):
        return "%s   pip install" % source_profile

    undone_packages = []

    def done(self):
        import pkg_resources

        for pkg1 in self.packages():
            print "[try pkg]", pkg1
            try:
                pkg_resources.require(pkg1)  # support version
            except Exception:
                print "[pkg is not done]", pkg1
                self.undone_packages.append(pkg1)
        self.packages = lambda: self.undone_packages
        return len(self.undone_packages) == 0


class LuigiEnv(PipEnv):
    def requires(self):
        return [PipEnv, LuigiDepYumPackages]

    def packages(self):
        return [
            "luigi==1.1.2",
            "snakebite==2.5.2", ]


class DjangoEnv(PipEnv):
    def requires(self):
        return [PipEnv]

    def packages(self):
        return ["django", "flup", ]


class PipCommonEggs(PipEnv):
    """ 通用 Python 第三方包 """
    def requires(self):
        return PipEnv


def detect_install_queue(env, install_queue=[]):
    """ Detect env queue recursively. """

    _env = env()
    if _env.done():
        print "[info]", env.__name__, "is already done."
        return install_queue
    else:
        install_queue.insert(0, env)

    requires = _env.requires()
    if not isinstance(requires, list):
        requires = [requires]
    for required_env in requires:
        detect_install_queue(required_env, install_queue)

    return install_queue


def run(env):
    install_queue = detect_install_queue(env)
    if install_queue:
        print "[install_queue]", [e1.__name__ for e1 in install_queue]

    for env1 in install_queue:
        env = env1
        env_name = "<" + env.__name__ + ">"
        _env = env()

        # change user
        # _env1_user = _env.user
        # _env_uid       = int(COMMANDS.getstatusoutput("id -u " + _env_user)[1])
        # os.seteuid(_env_uid)

        if _env.done():
            continue

        current_user = get_current_user()

        print
        print "[enter a env] running", env_name, "..."

        required_users = _env._users() or [lui_json["application_user"]]
        if current_user not in required_users:
            print "[error]", env_name, "requires user:", \
                  "\"" + str(_env._users()) + "\"", ", but current_user is", \
                  "\"" + current_user + "\"."
            print "[exit a env]", env_name, "..."
            exit()

        _env.run()
        print "[exit a env]", env_name, "..."

# import argparse # dont support Python 2.6, not builtin standard library.
# parser = argparse.ArgumentParser(description='Lui aims to setup deployment environment.')
# parser.add_argument('json_file', type=basestring, help='json config file for lui.')


example_json = """
{
    "linux_release_version": "centos",
    "root_user": "root",
    "application_user": "builtbot",
    "env": {
        "CommonYumPackages": {
            "attrs": {
                "packages": ["gcc", "gcc-c++", "g++", "make", "autoconf", "automake", "libtool", "bison", "rpm-build",
                    "zlib-devel", "openssl-devel", "readline-devel", "sqlite-devel", "bzip2-devel", "libxml2-devel", "libyaml-devel", "libffi-devel",
                    "git", "wget", "curl", "dkms", "nfs-utils", "screen", "vim", "tree", "telnet", "perl", "ruby", "python",
                    "python-devel", "libevent-devel", "libxslt-devel",
                    "mongodb-server", "mongodb", "mysql-devel", "mysqltuner",
                    "truss", "strace", "lstrace", "htop", "lsof", "iostat", "vmstat", "iftop",
                    "numpy", "scipy", "sympy", "blas-devel", "lapack-devel"
                ]
            }
        },
        "PythonDepYumPackages": {
            "attrs": {
                "packages": ["patch", "libtiff-devel", "libjpeg-devel", "freetype-devel", "openssl-devel", "readline-devel",
                    "libzip-devel", "bzip2-devel", "lcms2-devel", "python-devel", "sqlite-devel", "tcl-devel", "tk-devel"]
            }
        },
        "AddUserEnv": {
            "attrs": {
                "custom_user": "buildbot"
            }
        },
        "PipCommonEggs": {
            "attrs": {
                "packages": [
                    "pysqlite",
                    "pysqlite",
                    "pymongo==2.7.2 # 3.0 更新API了, 没有 AttributeError: 'module' object has no attribute 'Connection'",
                    "sqlalchemy",
                    "peewee",
                    "mongoengine",
                    "MySQL-python",

                    "model_cache",
                    "arrow",
                    "bunch",
                    "inflector",
                    "unicodecsv",
                    "statistics",
                    "python-dateutil #   # not dateutil",
                    "PyYAML",
                    "cached_property",
                    "joblib",

                    "mercurial",
                    "pip",

                    "numpy"]
            }
        }

    },
    "env_run_with_first": [
        "AddUserEnv",
        "PythonDepYumPackages"
    ]
}
"""

if __name__ == '__main__':
    # args_main = parser.parse_args()
    # json_file = args_main.json_file
    if len(sys.argv) < 2:
        raise ValueError("[error] Please provide a json file ... example json is \n\n\n %s" % example_json)

    json_file = sys.argv[1]
    lui_json = json.loads(file(json_file).read())

    assert "env" in lui_json, """%s has no "env" key""" % lui_json

    # TODO check key exists

    env_dict = lui_json["env"]
    for env_cls_name in env_dict.keys():
        env_cls = locals()[env_cls_name]
        for k1, v1 in env_dict[env_cls_name]["attrs"].iteritems():
            # to bind variable in loop.
            v1_wrap = (lambda v1: lambda self: v1)(v1)
            setattr(env_cls, k1, v1_wrap)

    env_to_run_cls = locals()[lui_json["env_run_with_first"][0]]
    run(env_to_run_cls)
