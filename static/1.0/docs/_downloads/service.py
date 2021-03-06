# File name: service.py
#
# The service module defines a single class (TGWindowsService) that contains
# the functionality for running a TurboGears application as a Windows Service.
# 
# To use this class, users must do the following:
# 1. Download and install the win32all package
#    (http://starship.python.net/crew/mhammond/win32/)
# 2. Edit the "USER EDIT SECTION" with the proper information.
#    If the standard TurboGears structure is being used (e.g. the one generated by 
#    quickstart), and this file is located in the base directory of the TG 
#    application, then no edits are required.
# 3. Open a command prompt and navigate to the directory where this file
#    is located.  Use one of the following commands to
#    install/start/stop/remove the service:
#    > service.py install
#    > service.py start
#    > service.py stop
#    > service.py remove
#    Additionally, typing "service.py" will present the user with all of the
#    available options.
#
# Once installed, the service will be accessible through the Services
# management console just like any other Windows Service.  All service 
# startup exceptions encountered by the TGWindowsService class will be 
# viewable in the Windows event viewer (this is useful for debugging
# service startup errors); all application specific output or exceptions that
# are not captured by the standard TG logging mechanism should 
# appear in the stdout/stderr logs.
#
# This module has been tested on Windows Server 2000, 2003, and Windows
# XP Professional.
#
# Note 1: If this file is not located in the application's base directory, 
# then make sure to edit the USER EDIT SECTION with the appropriate
# values.
#
# Note 2: The CherryPy autoreload functionality will not function when CherryPy
# is run as a Windows service, so the TGWindowsService class will automatically
# disable autoreloading before starting the server.

import pkg_resources
pkg_resources.require("TurboGears")

import turbogears
import cherrypy
cherrypy.lowercase_api = True

import sys
import os
from os.path import *

import win32serviceutil
import win32service
from win32com.client import constants

class TGWindowsService(win32serviceutil.ServiceFramework):
    """TurboGears Windows Service helper class.

    The TGWindowsService class contains all the functionality required
    for running a TurboGears application as a Windows Service.  The only
    user edits required for this class are located in the following class
    variables:
    
    _svc_name_:         The name of the service (used in the Windows registry).
                        DEFAULT: The capitalized name of the current directory.
    _svc_display_name_: The name that will appear in the Windows Service Manager.
                        DEFAULT: The capitalized name of the current directory.    
    code_dir:           The full path to the base directory of the user's
                        TG app code (usually where <project_name>-start.py
                        and the *.cfg files are located).
                        DEFAULT: The directory where this file is located.
    root_class:         The fully qualified Root class name
                        (e.g. wiki20.controllers.Root)
                        DEFAULT: <current_dir_name>.controllers.Root
    config_module:      The name of the configuration module.
                        DEFAULT: <current_dir_name>.config
    log_dir:            The desired location of the stdout and stderr
                        log files.
                        DEFAULT: code_dir
          
    For information on installing the application, please refer to the
    documentation at the end of this module or navigate to the directory
    where this module is located and type "service.py" from the command
    prompt.
    """
    current_dir = os.path.split(__file__)[0]
    default_project_name = os.path.split(current_dir)[1]

    # -- START USER EDIT SECTION
    # -- Users must edit this section before installing the service.
    _svc_name_ = '%s' % default_project_name.capitalize()           # The name of the service.
    _svc_display_name_ = '%s' % default_project_name.capitalize()   # The Service Manager display name.
    code_dir = current_dir                                          # The base directory of the TG app code.        
    root_class = '%s.controllers.Root' % default_project_name       # The fully qualified Root class name.
    config_module = '%s.config' % default_project_name              # The name of the config module
    log_dir = r''                                                   # The log directory for the stderr and 
                                                                    # stdout logs. Default = code_dir.
    # -- END USER EDIT SECTION
    
    def SvcDoRun(self):
        """ Called when the Windows Service runs. """

        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        self.tg_init()
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        turbogears.start_server(self.root())
    
    def SvcStop(self):
        """Called when Windows receives a service stop request."""
        
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        cherrypy.server.stop()
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def tg_init(self):
        """ Checks for the required data and initializes the application. """

        if TGWindowsService.code_dir:
            os.chdir(TGWindowsService.code_dir)
            sys.path.append(TGWindowsService.code_dir)
            # Redirect stdout and stderr to avoid buffer crashes.            
            sys.stdout = open(join(TGWindowsService.log_dir, 'stdout.log'),'a')
            sys.stderr = open(join(TGWindowsService.log_dir, 'stderr.log'),'a')
        else:
            raise ValueError("""The code directory setting is missing.
                                The Windows Service will not run
                                without this setting.""")

        if not TGWindowsService.root_class:
            raise ValueError("""The fully qualified root class name must
                                be provided.""")

        if not TGWindowsService.log_dir:
            TGWindowsService.log_dir = '.'

        if exists(join(dirname(__file__), "setup.py")):
            turbogears.update_config(configfile="dev.cfg",
                modulename=TGWindowsService.config_module)
        else:
            turbogears.update_config(configfile="prod.cfg",
                modulename=TGWindowsService.config_module)

        # Set environment to production to disable auto-reload.
        cherrypy.config.update({'global': {'server.environment': 'production'},})

        # Parse out the root class information and set it to self.root
        full_class_name = TGWindowsService.root_class
        last_mark = full_class_name.rfind('.')
        
        if (last_mark < 1) or (last_mark + 1) == len(full_class_name):
            raise ValueError("""The user-defined class name is invalid.
                                Please make sure to include a fully
                                qualified class name for the root_class
                                value (e.g. wiki20.controllers.Root).""")
        
        package_name = full_class_name[:last_mark]
        class_name = full_class_name[last_mark+1:]
        exec('from %s import %s as Root' % (package_name, class_name))
        self.root = Root
     
if __name__ == '__main__':
    # The following are the most common command-line arguments that are used
    # with this module:
    #  service.py install (Installs the service with manual startup)
    #  service.py --startup auto install (Installs the service with auto startup)    
    #  service.py start (Starts the service)
    #  service.py stop (Stops the service)
    #  service.py remove (Removes the service)
    #
    # For a full list of arguments, simply type "service.py".
    win32serviceutil.HandleCommandLine(TGWindowsService)

