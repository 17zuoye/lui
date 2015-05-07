#!/usr/bin/env python
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

current_user = os.getenv("USER", COMMANDS.getoutput("whoami"))
cmd = COMMANDS.getoutput


# TODO assert env is ready
# 1. whoami
# 2. yum, rpm

class Env(object):
    """ Package install env. """

    dry = False
    verbose = True

    _user = None  # default to current run user

    @property
    def user(self):
        return self._user or lui["lui_json"]["application_user"]

    @property
    def users(self):
        return [self.user]

    @property
    def name(self):
        return "<" + self.__class__.__name__ + ">"

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
        return list(set(_us))


class PackageEnv(Env):

    def run(self):
        """ Run the install shell scripts"""
        # 1 build shell command list
        commands = ["%s %s" % (self.run_cmd(), pkg1) for pkg1 in self.packages()]

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

    @property
    def _user(self):
        return lui["lui_json"]["root_user"]

    def run_cmd(self):
        return "%s    yum -y install" % lui["source_profile"]

    def done(self):
        """ `rpm -qa` 返回的是一行一行软件包，但是没有空格符。 """
        done_list = COMMANDS.getstatusoutput("rpm -qa")[1]
        needed_rpm_packages = self.packages()
        is_all_done = True
        for rpm_package in needed_rpm_packages:
            if rpm_package not in done_list:
                print "[error] %s is not done." % rpm_package
                is_all_done = False
                break
        return is_all_done


class ShellBehavior(Env):

    def run(self):
        context = "\n".join([
            lui["source_profile"],
            self.shell_scripts(),
        ])
        print "[command]", context
        os.system(context)

    def shell_scripts(self):
        raise NotImplementedError

    output_file = lambda: "/not exists!"

    def done(self):
        return os.path.exists(self.output_file())


class AddUserEnv(ShellBehavior):

    @property
    def _user(self):
        return lui["lui_json"]["root_user"]

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

            su - $USERNAME
            cd /home/$USERNAME
            mkdir -p .ssh
            touch .ssh/authorized_keys
            chmod 0600 .ssh/authorized_keys
            chmod -R 0700 .ssh
            chown -R $USERNAME:$USERNAME .ssh
        """ % self.to_add_user


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


class PyenvEnv(ShellBehavior):

    def requires(self):
        return ["InstallGit"]

    def done(self):
        pyenv_path = cmd("%s; which pyenv" % lui["source_profile"])
        return os.path.exists(pyenv_path)

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
          source                                                        .bash_profile
          """


class PyenvInstalPython279(ShellBehavior):

    def requires(self):
        return PyenvEnv

    def done(self):
        # Fix PYENV_ROOT env set in /etc/profile
        pyenv_root = cmd("%; pyenv root" % lui["source_profile"])
        return os.path.exists(os.path.join(pyenv_root, "versions/2.7.9"))

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
        return "%s   pip install" % lui["source_profile"]

    undone_packages = []

    def done(self):
        import pkg_resources

        for pkg1 in self.packages():
            pkg1 = pkg1.split(" ")[0]
            print u"[info] try pkg \"%s\"." % pkg1
            try:
                pkg_resources.require(pkg1)  # support version
            except Exception:
                print "[info] pkg \"%s\" is not done." % pkg1
                self.undone_packages.append(pkg1)
        self.packages = lambda: self.undone_packages
        return len(self.undone_packages) == 0


def detect_install_queue(env, install_queue=[]):
    """ Detect env queue recursively. """

    _env = env()
    print "[check a env] %s" % _env.name
    if _env.done():
        print "[info]", env.__name__, "is already done."
        return install_queue
    else:
        if env not in install_queue:
            install_queue.insert(0, env)

    requires = _env.requires()
    if not isinstance(requires, list):
        requires = [requires]
    for required_env in requires:
        if isinstance(required_env, basestring):
            required_env = lui[required_env]
        detect_install_queue(required_env, install_queue)

    return install_queue


def run(env):
    install_queue = detect_install_queue(env)
    if install_queue:
        print "[install_queue]", [e1.__name__ for e1 in install_queue]

    for env1 in install_queue:
        env = env1
        _env = env()

        # change user
        # TODO run `su - user "python __file__"`
        # _env1_user = _env.user
        # _env_uid       = int(COMMANDS.getstatusoutput("id -u " + _env_user)[1])
        # os.seteuid(_env_uid)

        if _env.done():
            continue

        print
        print "[enter a env] running", _env.name, "..."

        required_users = _env._users()
        if len(required_users) == 0:
            required_users = [lui["lui_json"]["application_user"]]

        if current_user not in required_users:
            print "[error]", _env.name, "requires user:", \
                  "\"" + str(_env._users()) + "\"", ", but current_user is", \
                  "\"" + current_user + "\"."
            print "[exit a env]", _env.name, "..."
            exit()

        _env.run()
        print "[exit a env]", _env.name, "..."


def load_params():
    if len(sys.argv) < 2:
        print ValueError("[error] Please provide a json file ... \n see example json at https://raw.githubusercontent.com/17zuoye/lui/master/test_lui.json ")
        exit()

    json_file = sys.argv[1]
    lui["lui_json"] = json.loads(file(json_file).read())
    lui["source_profile"] = lui["lui_json"].get("source_profile", "")


def get_env_run_task():
    env_dict = lui["lui_json"]["env"]
    for env_cls_name in env_dict.keys():
        env_cls_name = str(env_cls_name)  # compact with Python
        # 1. get or create a env class
        env_cls = lui[env_cls_name]
        if env_cls is None:
            assert "task_type" in env_dict[env_cls_name], "%s is missing a task_type, e.g. ShellBehavior" % env_cls_name
            task_type_str = str(env_dict[env_cls_name]["task_type"])
            assert lui[task_type_str], "can't find a task class %s." % task_type_str
            inherit_class = lui[task_type_str]
            env_cls = type(task_type_str, (inherit_class, ), {"__doc__": env_dict[env_cls_name].get("doc", None)})
            setattr(env_cls, "__name__", env_cls_name)
            lui[env_cls_name] = env_cls  # bind cls to local

        # 2. set attrs
        for k1, v1 in env_dict[env_cls_name]["attrs"].iteritems():
            # 2.1 fix value
            if k1 == "shell_scripts":
                if isinstance(v1, list):
                    v1 = u";\n".join(v1)
            # 2.2 to bind variable in loop.
            v1_wrap = (lambda v1: lambda self: v1)(v1)
            setattr(env_cls, k1, v1_wrap)


class lui_env(dict):
    """ delegate to globals(). """
    def __missing__(self, k1):
        return globals().get(k1, None)
lui = lui_env()


if __name__ == '__main__':
    # TODO check key exists

    load_params()
    get_env_run_task()

    env_to_run_cls = lui[lui["lui_json"]["env_run_with_first"][0]]
    run(env_to_run_cls)
