#!/usr/bin/env python
#
# Copyright (c) 2013 Marin Atanasov Nikolov <dnaeon@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer
#    in this position and unchanged.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR(S) ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR(S) BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"""
A Python script that automates the creation of SSH chroot(8) environments
"""

import os
import pwd
import grp
import sys
import shutil
import subprocess

# define the chroot base directory and the tools you want to have in the SSH jail
CHROOT_BASE = '/home/chroot'
APPS        = ['/bin/sh', 	    	'/bin/bash', 		'/usr/bin/id',
               '/bin/hostname',     	'/bin/ls', 		'/bin/cat',
               '/bin/grep',		'/usr/bin/cut',		'/usr/bin/find',
               ]

def shlibs(f):
    """
    Finds all shared libraries for a given file/application.

    Returns:
    	A list of the shared libraries for the given file/application

    Raises:
    	IOError

    """
    if not os.path.exists(f):
        raise IOError, '%s does not exists' % f

    # get the shared libraries
    try:
        ldd_output = subprocess.check_output(['/usr/bin/ldd', f]).split('\n')
    except subprocess.CalledProcessError:
        return []
        
    shlibs = []
    for eachLib in ldd_output:
        # ignore empty lines
        if not eachLib:
            continue

        # get all components of the shared library
        libInfo = eachLib.split()
            
        # special case, ignore the virtual shared library
        if os.path.splitext(libInfo[0])[0] == 'linux-vdso.so':
            continue

        if libInfo[1] == '=>':
            shlibs.append(libInfo[2])
        else:
            shlibs.append(libInfo[0])
                
    return shlibs

def chroot_install_apps(user_chroot, force_overwrite=False):
    """
    Installs the applications into the chroot(8) environment

    """
    print '=> (Re)installing applications in the chroot(8) environment'
    
    for eachApp in APPS:
        app_dir  = os.path.dirname(eachApp)
        app_name = os.path.basename(eachApp)

        if app_dir.startswith('/'):
            app_chroot_dir = os.path.join(user_chroot, app_dir[1:])
        else:
            app_chroot_dir = os.path.join(user_chroot, app_dir)

        app_chroot_location = os.path.join(app_chroot_dir, app_name)
            
        if not os.path.exists(app_chroot_dir):
            print '    * Creating chroot directory => %s' % app_chroot_dir
            os.makedirs(app_chroot_dir)

        if not os.path.exists(app_chroot_location) or \
                (os.path.exists(app_chroot_location) and force_overwrite):
            print '    * Installing chroot app => %s' % app_chroot_location
            shutil.copy2(eachApp, app_chroot_location)

def chroot_install_shlibs(user_chroot, force_overwrite=False):
    """
    Installs the shared libraries required by the applications

    """
    print '=> (Re)installing shared libraries in the chroot(8) environment'

    for eachApp in APPS:
        for eachLib in shlibs(eachApp):
            shlib_dir  = os.path.dirname(eachLib)
            shlib_name = os.path.basename(eachLib)

            if shlib_dir.startswith('/'):
                shlib_chroot_dir = os.path.join(user_chroot, shlib_dir[1:])
            else:
                shlib_chroot_dir = os.path.join(user_chroot, shlib_dir)

            shlib_chroot_location = os.path.join(shlib_chroot_dir, shlib_name)
                
            if not os.path.exists(shlib_chroot_dir):
                print '    * Creating chroot directory => %s' % shlib_chroot_dir
                os.makedirs(shlib_chroot_dir)

            if not os.path.exists(shlib_chroot_location) or \
                    (os.path.exists(shlib_chroot_location) and force_overwrite):
                print '    * Installing chroot shlib => %s' % shlib_chroot_location
                shutil.copy2(eachLib, shlib_chroot_location)

    print '    * (Re)installing /lib/terminfo'
    if not os.path.exists(os.path.join(user_chroot, 'lib/terminfo')):
        shutil.copytree('/lib/terminfo', os.path.join(user_chroot, 'lib/terminfo'))
    else:
        shutil.rmtree(os.path.join(user_chroot, 'lib/terminfo'))
        shutil.copytree('/lib/terminfo', os.path.join(user_chroot, 'lib/terminfo'))

    print '    * (Re)installing /usr/lib/locale'
    if not os.path.exists(os.path.join(user_chroot, 'usr/lib/locale')):
        shutil.copytree('/usr/lib/locale', os.path.join(user_chroot, 'usr/lib/locale'))
    else:
        shutil.rmtree(os.path.join(user_chroot, 'usr/lib/locale'))
        shutil.copytree('/usr/lib/locale', os.path.join(user_chroot, 'usr/lib/locale'))
        
def chroot_create_base_dirs(user_chroot):
    """
    Creates the base chroot dir and the user's chroot directory

    """
    print '=> Creating/updating base chroot(8) directories'
    
    if not os.path.exists(CHROOT_BASE):
        print '    * Creating chroot base => %s' % CHROOT_BASE
        os.makedirs(CHROOT_BASE)

    if not os.path.exists(user_chroot):
        print '    * Creating chroot directory => %s' % user_chroot
        os.makedirs(user_chroot)

    if not os.path.exists(os.path.join(user_chroot, 'root')):
        print '    * Creating chroot directory => /root'
        os.makedirs(os.path.join(user_chroot, 'root'))
        os.chmod(os.path.join(user_chroot, 'root'), 0700)
        
def chroot_create_dev(user_chroot):
    """
    Creates /dev entries in the chroot environment

    """
    print '=> (Re)creating /dev entries for the chroot(8) environment'
    
    if not os.path.exists(os.path.join(user_chroot, 'dev')):
        print '    * Creating chroot /dev directory'
        os.makedirs(os.path.join(user_chroot, 'dev'))
    
    if not os.path.exists(os.path.join(user_chroot, 'dev/null')):
        print '    * Creating chroot dev entry => /dev/null'
        subprocess.call(['/bin/mknod', '-m', '666', os.path.join(user_chroot, 'dev/null'), 'c', '1', '3'])

    if not os.path.exists(os.path.join(user_chroot, 'dev/zero')):
        print '    * Creating chroot dev entry => /dev/zero'
        subprocess.call(['/bin/mknod', '-m', '666', os.path.join(user_chroot, 'dev/zero'), 'c', '1', '5'])

    if not os.path.exists(os.path.join(user_chroot, 'dev/random')):
        print '    * Creating chroot dev entry => /dev/random'
        subprocess.call(['/bin/mknod', '-m', '666', os.path.join(user_chroot, 'dev/random'), 'c', '1', '8'])

    if not os.path.exists(os.path.join(user_chroot, 'dev/urandom')):
        print '    * Creating chroot dev entry => /dev/urandom'
        subprocess.call(['/bin/mknod', '-m', '666', os.path.join(user_chroot, 'dev/urandom'), 'c', '1', '9'])

def chroot_create_etc(user_chroot):
    """
    Creates /etc entries in the chroot environment

    NOTE: We do not test whether files exists before they are actually installed on the
    chroot(8)'ed environment. Reason why we don't do that check is to allow easier updates of the
    chroot environment.
    
    """
    print '=> Creating /etc entries for the chroot(8) environment'
    
    chroot_etc_dir = os.path.join(user_chroot, 'etc')
    
    if not os.path.exists(chroot_etc_dir):
        print '    * Creating chroot directory => /etc'
        os.makedirs(chroot_etc_dir)

#    print '    * Installing chroot file => /etc/passwd'
#    shutil.copy2('/etc/passwd', os.path.join(chroot_etc_dir, 'passwd'))

#    print '    * Installing chroot file => /etc/group'
#    shutil.copy2('/etc/group', os.path.join(chroot_etc_dir, 'group'))
    
    print '    * Installing chroot file => /etc/profile'
    shutil.copy2('/etc/profile', os.path.join(chroot_etc_dir, 'profile'))

    print '    * Installing chroot file => /etc/hosts'
    shutil.copy2('/etc/hosts', os.path.join(chroot_etc_dir, 'hosts'))

    print '    * Installing chroot file => /etc/services'
    shutil.copy2('/etc/services', os.path.join(chroot_etc_dir, 'services'))

    if not os.path.exists(os.path.join(chroot_etc_dir, 'profile.d')):
        print '    * Installing chroot file => /etc/profile.d'
        shutil.copytree('/etc/profile.d', os.path.join(chroot_etc_dir, 'profile.d'))
    else:
        print '    * Re-installing chroot file => /etc/profile.d'
        shutil.rmtree(os.path.join(chroot_etc_dir, 'profile.d'))
        shutil.copytree('/etc/profile.d', os.path.join(chroot_etc_dir, 'profile.d'))

    if not os.path.exists(os.path.join(chroot_etc_dir, 'skel')):
        print '    * Installing chroot file => /etc/skel'
        shutil.copytree('/etc/skel', os.path.join(chroot_etc_dir, 'skel'))
    else:
        print '    * Re-installing chroot file => /etc/skel'
        shutil.rmtree(os.path.join(chroot_etc_dir, 'skel'))
        shutil.copytree('/etc/skel', os.path.join(chroot_etc_dir, 'skel'))

    print '    * (Re)installing chroot file => /etc/locale.alias'
    shutil.copy2('/etc/locale.alias', os.path.join(chroot_etc_dir, 'locale.alias'))

    print '    * (Re)installing chroot file => /etc/locale.gen'
    shutil.copy2('/etc/locale.gen', os.path.join(chroot_etc_dir, 'locale.gen'))
        
def chroot_create_user(user, user_chroot):
    """
    Creates the user and sets up the home directory

    """
    try:
        # get the user's home directory
        user_home = pwd.getpwnam(user)[5]
        print "=> Updating user's chroot => %s" % user
    except KeyError as e:
        print '=> User does not exists, will create it now ...'
        subprocess.call(['/usr/sbin/adduser', user])
        user_home = pwd.getpwnam(user)[5]

    # TODO: Add users to the SSH_GROUP group
        
    # we need to create the home directory of the user inside the chroot as well
    # and populate it with /etc/skel files
    if not os.path.exists(os.path.join(user_chroot, user_home[1:])):
        print '    * Installing chroot files => skel files for %s' % user
        shutil.copytree('/etc/skel', os.path.join(user_chroot, user_home[1:]))
    else:
        print '    * Re-installing chroot files => skel files for %s' % user
        shutil.rmtree(os.path.join(user_chroot, user_home[1:]))
        shutil.copytree('/etc/skel', os.path.join(user_chroot, user_home[1:]))

def chroot_install_usr_share(user_chroot):
    """
    Installs man pages and documentation in the chroot environment

    """
    print '=> Installing documentation in the chroot(8) environment'
    
    if not os.path.exists(os.path.join(user_chroot, 'usr/share/locale')):
        print '    * Installing chroot locales => /usr/share/locale'
        shutil.copytree('/usr/share/locale', os.path.join(user_chroot, 'usr/share/locale'))
    else:
        print '    * Re-installing chroot locales => /usr/share/locale'
        shutil.rmtree(os.path.join(user_chroot, 'usr/share/locale'))
        shutil.copytree('/usr/share/locale', os.path.join(user_chroot, 'usr/share/locale'))
        
def main():
    if len(sys.argv) != 2:
        print 'usage: %s <username>' % sys.argv[0]
        raise SystemExit

    user = sys.argv[1]
    user_chroot = os.path.join(CHROOT_BASE, user)

    chroot_create_base_dirs(user_chroot)
    chroot_create_user(user, user_chroot)
    chroot_create_dev(user_chroot)
    chroot_create_etc(user_chroot)
    chroot_install_apps(user_chroot)
    chroot_install_shlibs(user_chroot)
    chroot_install_usr_share(user_chroot)

    print '=> Chroot environment is ready.'
    
if __name__ == '__main__':
    main()
