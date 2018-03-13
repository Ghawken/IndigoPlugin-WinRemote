#! /usr/bin/env python2.6
# -*- coding: utf-8 -*-

"""
Windows Remote Software for Indigo Plugin

Needs to be used in combination with a Windows app
'Indigo Plugin Communicator'

Essentially useless alone.!

"""


import logging

import ast
import subprocess
import threading
import struct
import socket
import json

## Role together own httpserver
import string
from urlparse import urlparse, parse_qsl
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn


import sys
import time as t

from ghpu import GitHubPluginUpdater

try:
    import indigo
except:
    pass

# Establish default plugin prefs; create them if they don't already exist.
kDefaultPluginPrefs = {
    u'configMenuPollInterval': "300",  # Frequency of refreshes.
    u'configMenuServerTimeout': "15",  # Server timeout limit.
    # u'refreshFreq': 300,  # Device-specific update frequency
    u'showDebugInfo': False,  # Verbose debug logging?
    u'configUpdaterForceUpdate': False,
    u'configUpdaterInterval': 24,
    u'showDebugLevel': "1",  # Low, Medium or High debug output.
    u'updaterEmail': "",  # Email to notify of plugin updates.
    u'updaterEmailsEnabled': False,  # Notification of plugin updates wanted.
    u'serverport':9123
}


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.startingUp = True
        self.pluginIsShuttingDown = False

        self.versionPlugin = pluginVersion

        # Okay Versions across two applications
        # First Number 0 - ignore
        # Second Number is the Mac Version -- increasing this without breaking PC app versions
        # Third Number is the PC Version --
        # e.g 0.2.2 -- 2 is current mac version, 2 is current PC version
        # if version goes to 0.2.4  -- PC version needs to be updated if less than 4 and will organise message
        # if version is 0.4.2 -- PC version remains on 2 - so only Mac update needed/done.

        self.listenPort  = 9123

        self.logger.info(u"")
        self.logger.info(u"{0:=^130}".format(" Initializing New Plugin Session "))
        self.logger.info(u"{0:<30} {1}".format("Plugin name:", pluginDisplayName))
        self.logger.info(u"{0:<30} {1}".format("Plugin version:", pluginVersion))
        self.logger.info(u"{0:<30} {1}".format("Plugin ID:", pluginId))
        self.logger.info(u"{0:<30} {1}".format("Indigo version:", indigo.server.version))
        self.logger.info(u"{0:<30} {1}".format("Python version:", sys.version.replace('\n', '')))
        self.logger.info(u"{0:=^130}".format(""))

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)

        try:
            self.logLevel = int(self.pluginPrefs[u"showDebugLevel"])
        except:
            self.logLevel = logging.INFO

        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u"logLevel = " + str(self.logLevel))
        self.triggers = {}

        self.validatePrefsConfigUi(pluginPrefs)

        self.debugLevel = self.pluginPrefs.get('showDebugLevel', "20")
        self.debugextra = self.pluginPrefs.get('debugextra', False)


        self.debugserver = True

        #self.configUpdaterForceUpdate = self.pluginPrefs.get('configUpdaterForceUpdate', False)
        self.openStore = self.pluginPrefs.get('openStore', False)
        self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
        self.next_update_check = t.time() + 20
        self.pluginIsInitializing = False

        #self.startlistenHttpThread()


    def __del__(self):
        if self.debugLevel >= 2:
            self.debugLog(u"__del__ method called.")
        indigo.PluginBase.__del__(self)

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if self.debugLevel >= 2:
            self.debugLog(u"closedPrefsConfigUi() method called.")

        if userCancelled:
            self.debugLog(u"User prefs dialog cancelled.")

        if not userCancelled:
            self.debugLevel = valuesDict.get('showDebugLevel', "10")
            self.debugLog(u"User prefs saved.")
            self.listenPort = int(valuesDict.get('serverport',9123))
            self.debugextra = valuesDict.get('debugextra', False)
            try:
                self.logLevel = int(valuesDict[u"showDebugLevel"])
            except:
                self.logLevel = logging.INFO

            self.indigo_log_handler.setLevel(self.logLevel)
            self.logger.debug(u"logLevel = " + str(self.logLevel))

        return True

    def validateDeviceConfigUi(self, valuesDict, typeID, devId):
        self.logger.debug(u'validateDeviceConfigUi Called')
        errorDict = indigo.Dict()
        return (True, valuesDict, errorDict)



    def validatePrefsConfigUi(self, valuesDict):
        """ docstring placeholder """
        self.logger.debug(u"------ validatePrefsConfigUi() method called.")
        errorDict = indigo.Dict()
        if 'serverport' in valuesDict:
            try:
                # self.logger.debug(u'Old listenPort is :' + unicode(self.oldlistenPort))
                self.listenPort = int(valuesDict['serverport'])
            except:
                # self.logger.exception(u'Httpserverport Error')
                self.listenPort = 9123
                self.pluginPrefs['serverport'] = 9123
                errorDict['serverport'] = 'Please enter valid Port Number'
                errorDict['showAlertText'] = 'The field is invalid as it is not an integer'
                return (False, valuesDict, errorDict)

        #self.logger.info(unicode(valuesDict))
        return True, valuesDict

    def restartPlugin(self):
        self.logger.debug(u"Restarting the  Plugin Called.")
        plugin = indigo.server.getPlugin('com.GlennNZ.indigoplugin.WinRemote')
        if plugin.isEnabled():
            plugin.restart(waitUntilDone=False)


    # Start 'em up.
    def deviceStartComm(self, dev):
        self.logger.debug(u"deviceStartComm() method called.")
        dev.stateListOrDisplayStateIdChanged()
        dev.updateStateOnServer('pendingCommands', value='', uiValue='None')

        dev.updateStateOnServer('onOffState', value=False)
        dev.updateStateOnServer('deviceIsOnline', value=False)

    def createupdatevariable(self, variable, result):

        if self.debugextra:
            self.logger.debug(u'createupdate variable called.')

        if variable not in indigo.variables:
            indigo.variable.create(variable, str(result), folder='WinRemote')
            return
        else:
            indigo.variable.updateValue(str(variable), str(result))
        return

    # Shut 'em down.

    def deviceStopComm(self, dev):
        self.logger.debug(u"deviceStopComm() method called.")
        #indigo.server.log(u"Stopping device: " + dev.name)

    def runConcurrentThread(self):

        try:
            self.checkComputers = t.time() + 10  # check for offline every 60 seconds
            while self.pluginIsShuttingDown == False:

                self.prefsUpdated = False
                self.sleep(0.5)


                if self.updateFrequency > 0:
                    if t.time() > self.next_update_check:
                        try:
                            self.checkForUpdates()
                            self.next_update_check = t.time() + self.updateFrequency
                        except:
                            self.logger.debug(
                            u'Error checking for update - ? No Internet connection.  Checking again in 24 hours')
                            self.next_update_check = t.time() + 86400;

                if t.time() >= self.checkComputers:
                    self.checktheComputers()
                    self.checkComputers = t.time()+60

                # nothing else will run...
                self.sleep(1)


        except self.StopThread:
            self.logger.info(u'Restarting/or error. Stopping  thread.')
            pass

    def checktheComputers(self):
        if self.debugextra:
            self.logger.debug(u'checkComputers run')

        for dev in indigo.devices.itervalues('self.WindowsComputer'):
            if dev.enabled:
                if dev.states['deviceIsOnline']:

                    if (float(t.time())-120)> float(dev.states['deviceTimestamp']) :  #2 minutes no communication
                        self.logger.debug(u't.time +120 equals:'+unicode(float(t.time())+120))
                        self.logger.debug(u'Offline : deviceTimestamp:t.time:'+unicode(t.time())+' Timestamp:'+unicode(dev.states['deviceTimestamp']))
                        dev.updateStateOnServer('deviceIsOnline', value=False, uiValue='Offline')
                        dev.updateStateOnServer('onOffState', value=False)

        return

    def shutdown(self):

        self.logger.debug(u"shutdown() method called.")
        self.pluginIsShuttingDown = True
        self.prefsUpdated = True

    def startup(self):


        self.logger.debug(u"Starting Plugin. startup() method called.")
        self.updater = GitHubPluginUpdater(self)

        self.myThread = threading.Thread(target=self.listenHTTP, args=())
        self.myThread.daemon = True
        self.myThread.start()



    def toggleDebugEnabled(self):
        """ Toggle debug on/off. """

        self.logger.debug(u"toggleDebugEnabled() method called.")

        if self.debugLevel == int(logging.INFO):
            self.debug = True
            self.debugLevel = int(logging.DEBUG)
            self.pluginPrefs['showDebugInfo'] = True
            self.pluginPrefs['showDebugLevel'] = int(logging.DEBUG)
            self.logger.info(u"Debugging on.")
            self.logger.debug(u"Debug level: {0}".format(self.debugLevel))
            self.logLevel = int(logging.DEBUG)
            self.logger.debug(u"New logLevel = " + str(self.logLevel))
            self.indigo_log_handler.setLevel(self.logLevel)

        else:
            self.debug = False
            self.debugLevel = int(logging.INFO)
            self.pluginPrefs['showDebugInfo'] = False
            self.pluginPrefs['showDebugLevel'] = int(logging.INFO)
            self.logger.info(u"Debugging off.  Debug level: {0}".format(self.debugLevel))
            self.logLevel = int(logging.INFO)
            self.logger.debug(u"New logLevel = " + str(self.logLevel))
            self.indigo_log_handler.setLevel(self.logLevel)

#################################################################################################
    def pluginTriggering(self, valuesDict):
        self.logger.debug(u'pluginTriggering called')
        try:
            #self.logger.info(unicode(valuesDict))
            action = valuesDict.pluginTypeId
            actionevent = valuesDict.props['plugintriggersetting']
            cameras = valuesDict.props['deviceCamera']
            #self.logger.info(unicode(cameras))

            for dev in indigo.devices.itervalues('self.WindowsComputer'):
                if str(dev.id) in cameras:
                    self.logger.debug(u'Action is:' + unicode(action) + u' & Camera is:' + unicode(dev.name)+u' and action:'+unicode(actionevent))
                    if actionevent == 'False':
                        dev.updateStateOnServer('PluginTriggeringEnabled', value=False)
                        dev.updateStateOnServer('Motion', value=False ,uiValue='False')
                    if actionevent == 'True':
                        dev.updateStateOnServer('PluginTriggeringEnabled', value=True)
                        dev.updateStateOnServer('Motion', value=False, uiValue='False')
            return
        except:
            self.logger.exception(u'Caught Exception within pluginTriggerin')
##################  communication to Computers


##################  Triggers

    def triggerStartProcessing(self, trigger):
        self.logger.debug("Adding Trigger %s (%d) - %s" % (trigger.name, trigger.id, trigger.pluginTypeId))
        assert trigger.id not in self.triggers
        self.triggers[trigger.id] = trigger

    def triggerStopProcessing(self, trigger):
        self.logger.debug("Removing Trigger %s (%d)" % (trigger.name, trigger.id))
        assert trigger.id in self.triggers
        del self.triggers[trigger.id]

    def triggerCheck(self, device, camera, event):

        if self.debugtriggers:
            self.logger.debug('triggerCheck run.  device.id:'+unicode(device.id)+' Camera:'+unicode(camera)+' Event:'+unicode(event))
        try:
            if self.pluginIsInitializing:
                self.logger.info(u'Trigger: Ignore as WinRemote Plugin Just started.')
                return

            if device.states['deviceIsOnline'] == False:
                if self.debugtriggers:
                    self.logger.debug(u'Trigger Cancelled as Device is Not Online')
                return

            if device.states['PluginTriggeringEnabled'] ==False:
                if self.debugtriggers:
                    self.logger.debug(u'Plugin Triggering is Disable for this Camera')
                return


            for triggerId, trigger in sorted(self.triggers.iteritems()):

                if self.debugtriggers:
                    self.logger.debug("Checking Trigger %s (%s), Type: %s, Camera: %s" % (trigger.name, trigger.id, trigger.pluginTypeId, camera))
                    #self.logger.debug(unicode(trigger))
                #self.logger.error(unicode(trigger))
                # Change to List for all Cameras

                if str(device.id) not in trigger.pluginProps['deviceCamera']:
                    if self.debugtriggers:
                        self.logger.debug("\t\tSkipping Trigger %s (%s), wrong Camera: %s" % (trigger.name, trigger.id, device.id))
                elif trigger.pluginTypeId == "motionTriggerOn" and event =='motiontrue':
                    if self.debugtriggers:
                        self.logger.debug("===== Executing motionTriggerOn/motiontrue Trigger %s (%d)" % (trigger.name, trigger.id))
                    indigo.trigger.execute(trigger)
                elif trigger.pluginTypeId == "motionTriggerOff" and event =='motionfalse':
                    if self.debugtriggers:
                        self.logger.debug("===== Executing motionTriggerOff/motionfalse Trigger %s (%d)" % (trigger.name, trigger.id))
                    indigo.trigger.execute(trigger)
                else:
                    if self.debugtriggers:
                        self.logger.debug("Not Run Trigger Type %s (%d), %s" % (trigger.name, trigger.id, trigger.pluginTypeId))

        except:
            self.logger.exception(u'Caught Exception within Trigger Check')
            return
## Update routines

    def checkForUpdates(self):

        updateavailable = self.updater.getLatestVersion()
        if updateavailable and self.openStore:
            self.logger.info(u'WinRemote Plugin: Update Checking.  Update is Available.  Taking you to plugin Store. ')
            self.sleep(2)
            self.pluginstoreUpdate()
        elif updateavailable and not self.openStore:
            self.errorLog(u'WinRemote Plugin: Update Checking.  Update is Available.  Please check Store for details/download.')

    def updatePlugin(self):
        self.updater.update()

    def pluginstoreUpdate(self):
        iurl = 'http://www.indigodomo.com/pluginstore/'
        self.browserOpen(iurl)

######################

    def listenHTTP(self):
        try:
            self.debugLog(u"Starting HTTP listener thread")
            indigo.server.log(u"Http Server Listening on TCP port " + str(self.listenPort))
            self.server = ThreadedHTTPServer(('', self.listenPort), lambda *args: httpHandler(self, *args))
            self.server.serve_forever()

        except self.StopThread:
            self.logger.debug(u'Self.Stop Thread called')
            pass
        except:
            self.logger.exception(u'Caught Exception in ListenHttp')
################## Actions
    def actionControlDevice(self, action, dev):
        self.logger.debug(u'Turn On/Turn Off Called' )
        if action.deviceAction == indigo.kDeviceAction.TurnOff:
            turnOff = dev.pluginProps.get('turnOff', False)
            self.logger.debug(u"actionControlDevice: \"%s\" Turn Off" % dev.name)
            if turnOff==False:
                tobesent = {'COMMAND': 'OFF', 'COMMAND2': '', 'COMMAND3': '', 'COMMAND4': ''}
                dev.updateStateOnServer('pendingCommands', value=str(tobesent), uiValue='Pending...')
            else:
                self.logger.debug(u'Turn Off Command not sent as Disabled within Device Config')
            return
        elif action.deviceAction == indigo.kDeviceAction.TurnOn:
            self.logger.debug(u"actionControlDevice: \"%s\" Turn On" % dev.name)
            self.actionWakeMACbydevid(dev.id)
            return
        elif action.deviceAction == indigo.kDeviceAction.RequestStatus:
            self.logger.info(u'Send Status Not Supported.')
            return

    def actionrunProcess(self, valuesDict):
        self.logger.debug(u'Send Message Called.')
        try:
            computers = valuesDict.props['computer']
            process = valuesDict.props['process']
            arguments = valuesDict.props['arguments']
            for dev in indigo.devices.itervalues('self.WindowsComputer'):

                if str(dev.id) in computers:
                    tobesent = { 'COMMAND':'PROCESS','COMMAND2':str(process), 'COMMAND3':str(arguments),'COMMAND4':'' }
                    dev.updateStateOnServer('pendingCommands', value=str(tobesent), uiValue='Pending...')

        except:
            self.logger.exception(u'Exception in action Send Message')
        return


    def actionSendMessage(self, valuesDict):
        self.logger.debug(u'Send Message Called.')
        try:
            computers = valuesDict.props['computer']
            message = valuesDict.props['message']
            for dev in indigo.devices.itervalues('self.WindowsComputer'):
                if str(dev.id) in computers:
                    #tobesent = 'COMMAND MESSAGE',message
                    tobesent = {'COMMAND': 'MESSAGE', 'COMMAND2': str(message), 'COMMAND3':'','COMMAND4':'' }
                    dev.updateStateOnServer('pendingCommands', value=str(tobesent), uiValue='Pending...')
        except:
            self.logger.exception(u'Exception in action Send Message')
        return

    def actionRestart(self, valuesDict):
        self.logger.debug(u'Restart Command Called.')

        try:
            computers = valuesDict.props['computer']
            message = 'This computer will be restarted in 20 seconds'
            for dev in indigo.devices.itervalues('self.WindowsComputer'):
                if str(dev.id) in computers:
                    turnOff = dev.pluginProps.get('turnOff', False)
                    tobesent = {'COMMAND': 'RESTART','COMMAND2':'', 'COMMAND3':'','COMMAND4':'' }
                    # check device settings ignore if turn off ignored.
                    if turnOff == False:
                        dev.updateStateOnServer('pendingCommands', value=str(tobesent), uiValue='Pending...')
                    else:
                        self.logger.info(u'Restart Command not sent as Disabled within Device Config')
        except:
            self.logger.exception(u'Exception in action Send Message')
        return

    def actionTurnOff(self, valuesDict):
        self.logger.debug(u'Turn Off Called.')
        try:
            computers = valuesDict.props['computer']
            message = 'This computer will be turned off in 10 seconds'
            for dev in indigo.devices.itervalues('self.WindowsComputer'):
                if str(dev.id) in computers:
                    turnOff = dev.pluginProps.get('turnOff', False)

                   # tobesent = 'COMMAND OFF',message
                    tobesent = {'COMMAND': 'OFF','COMMAND2':'', 'COMMAND3':'','COMMAND4':'' }
                    if turnOff == False:
                        dev.updateStateOnServer('pendingCommands', value=str(tobesent), uiValue='Pending...')
                    else:
                        self.logger.debug(u'Turn Off Command not sent as Disabled within Device Config')
        except:
            self.logger.exception(u'Exception in action Send Message')
        return

    def actionLock(self, valuesDict):
        self.logger.debug(u'actionLock Message Called.')
        try:
            computers = valuesDict.props['computer']
            message = 'This computer will be Locked off in 10 seconds'
            for dev in indigo.devices.itervalues('self.WindowsComputer'):
                if str(dev.id) in computers:
                    tobesent = 'COMMAND LOCK',message
                    tobesent = {'COMMAND': 'LOCK','COMMAND2':'', 'COMMAND3':'','COMMAND4':'' }
                    dev.updateStateOnServer('pendingCommands', value=str(tobesent), uiValue='Pending...')
        except:
            self.logger.exception(u'Exception in action Lock')
        return

    def actionWakeMACbydevid(self,devid):
        self.logger.debug(u'actionWakeMAC by devid called')
        try:
            dev = indigo.devices[devid]
          # Take the entered MAC address and format it to be sent via socket
            if dev.states['MACaddress']!='unknown' or dev.states['MACaddress']!='':
                macaddress = str(dev.states['MACaddress'])
                #ipaddress = dev.states    if len(macaddress) == 12:
                if len(macaddress) == 12:
                    pass
                elif len(macaddress) == 17:
                    sep = macaddress[2]
                    macaddress = macaddress.replace(sep, '')
                else:
                    self.logger.debug(u'Wrong Format of MAC address ? not known.')
                    return
                data = b'FFFFFFFFFFFF' + (macaddress * 20).encode()
                self.logger.debug('Macaddress now:'+unicode(macaddress))

                send_data = b''
                # Split up the hex values in pack
                for i in range(0, len(data), 2):
                    send_data += struct.pack(b'B', int(data[i: i + 2], 16))

                self.packet = send_data

                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                self.logger.debug('sending magicPacket:')
                s.connect(('255.255.255.255',9))
                s.send(self.packet)
               # s.send(self.packet)
                s.close()
            else:
                self.logger.info(u'MAC Address not known as yet.')
                return
        except:
            self.logger.exception(u'Exception in Action wake MAC')


    def actionWakeMAC(self, valuesDict):
        self.logger.debug(u'actionWakeonLAN MAC called')
        try:
            computers = valuesDict.props['computer']
            for dev in indigo.devices.itervalues('self.WindowsComputer'):
                if str(dev.id) in computers:
                    # Take the entered MAC address and format it to be sent via socket
                    if dev.states['MACaddress']!='unknown' or dev.states['MACaddress']!='':
                        macaddress = str(dev.states['MACaddress'])
                        #ipaddress = dev.states    if len(macaddress) == 12:
                        if len(macaddress) == 12:
                            pass
                        elif len(macaddress) == 17:
                            sep = macaddress[2]
                            macaddress = macaddress.replace(sep, '')
                        else:
                            self.logger.debug(u'Wrong Format of MAC address ? not known.')
                            return
                        data = b'FFFFFFFFFFFF' + (macaddress * 20).encode()
                        self.logger.debug('Macaddress now:'+unicode(macaddress))

                        send_data = b''
                        # Split up the hex values in pack
                        for i in range(0, len(data), 2):
                            send_data += struct.pack(b'B', int(data[i: i + 2], 16))

                        self.packet = send_data

                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                        self.logger.debug('sending magicPacket:')
                        s.connect(('255.255.255.255',9))
                        s.send(self.packet)
                       # s.send(self.packet)
                        s.close()
        except:
            self.logger.exception(u'Exception in Action wake MAC')


################## Http Server

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

class httpHandler(BaseHTTPRequestHandler):
    def __init__(self,plugin, *args):
        self.plugin=plugin
        #self.logger = logger
        if self.plugin.debugextra:
            self.plugin.logger.debug(u'New Http Handler thread:'+threading.currentThread().getName()+", total threads: "+str(threading.activeCount()))
        BaseHTTPRequestHandler.__init__(self, *args)

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_POST(self):
        global rootnode
        if self.plugin.debugextra:
            self.plugin.logger.debug(u'Received Http POST')
            self.plugin.logger.debug(u'Sending HTTP 200 Response')
            self.plugin.logger.debug(u'Self Ip Address:'+unicode(self.client_address))
        try:

            content_length = int(self.headers['Content-Length'])  # <--- Gets the size of data
            post_data = self.rfile.read(content_length)  # <--- Gets the data itself
              # <-- Print post data
            windowspath = self.path
            windowsreply = str(post_data)

            if self.plugin.debugextra:
                self.plugin.logger.debug(u'self.path data:'+unicode(self.path))
                self.plugin.logger.debug(u'post.data data:'+unicode(post_data))


              # if StartupConnect will be Hostname

              # if StartupConnect will have StartupConnect within the path

            dictparams = dict(parse_qsl(urlparse(windowspath).query))
            if self.plugin.debugextra:
                self.plugin.logger.debug(unicode(dictparams))

            ## default to blank command set
            replytosend = { 'COMMAND':'','COMMAND2':'', 'COMMAND3':'', 'COMMAND4':'' }
            ## sort out replies later
            ## Send reply back to Computer depending on what is pending
            ## Only One Command possible at time
            # check not first connection startup, if so move on
            if 'StartupConnect' not in self.path:
                # need to check very device to see if matching hostname
                for dev in indigo.devices.itervalues('self.WindowsComputer'):
                    if dev.states['HostName'] == dictparams['Hostname']:
                        # okay reply from or for this specific device
                        # now check pending commands
                        if self.plugin.debugextra:
                            self.plugin.logger.debug('Command Matching HostName here...')
                        if str(dev.states['pendingCommands']) !='':
                            #commands = ast.literal_eval((dev.states['pendingCommands']))
                            #self.plugin.logger.error(unicode(commands[0]))
                            #self.plugin.logger.error(unicode(commands[1]))
                            #command = str(commands[0])
                            #command2 = str(commands[1])
                            #replytosend = command+' :'+command2+':'
                            # just send json
                            replytosend = dev.states['pendingCommands']
                            self.plugin.logger.info(u'Windows PC Command Sent to Device: '+unicode(dev.name));
                            if self.plugin.debugextra:
                                self.plugin.logger.debug('Command Processed: Sending reply:'+unicode(replytosend))
                            ## Delete the info
                            dev.updateStateOnServer('pendingCommands', value='', uiValue='None')
            ######

            self.send_response(200,str(replytosend))
            self.send_header('Content-type', 'text/html')
            self.send_header('IndigoPluginVersion',self.plugin.versionPlugin)
            self.send_header('IPAddress',str(self.client_address[0]))
            self.end_headers()

            # if self.plugin.debugserver:
            #     self.plugin.logger.debug(unicode('After Indigo Post Check'))

            if 'StartupConnect' in self.path:
                self.plugin.logger.debug(u'Startup of PC IndigoPlugin Noted:')
                FoundDevice = False
                for dev in indigo.devices.itervalues('self.WindowsComputer'):
                    #self.plugin.logger.debug(str(dev.states['HostName'])+': and :'+unicode(windowsreply))
                    if str(dev.states['HostName']) == windowsreply:
                        FoundDevice = True
                        #startup and device know - just update
                        if self.plugin.debugextra:
                            self.plugin.logger.debug(u'Do these Match?:'+str(dev.states['HostName']) + ': and :' + unicode(windowsreply))
                            self.plugin.logger.debug(u'Matching Hostname Found: '+windowsreply+' Updating States.')
                        t.sleep(0.5)
                        stateList = [
                            {'key': 'HostName', 'value': windowsreply},
                            {'key': 'deviceIsOnline', 'value': True},
                            {'key': 'onOffState', 'value': True},
                            {'key': 'deviceTimestamp', 'value': str(t.time())},
                            {'key': 'ipAddress', 'value': str(self.client_address[0])}
                        ]
                        dev.updateStatesOnServer(stateList)
                        # Create device and then return
                        return
                if FoundDevice == False:
                    # else Create Device
                    if self.plugin.debugextra:
                        self.plugin.logger.debug(u'Creating new Device for Windows Computer that has communicated.')
                    deviceName = 'Windows Computer: '+windowsreply
                    dev = indigo.device.create(address=deviceName, deviceTypeId='WindowsComputer', name=deviceName,
                                           protocol=indigo.kProtocol.Plugin, folder='Windows Computers')
                    t.sleep(1)
                # update here even if Startup...
                # no - can't do this -- what device? Fix
                    stateList = [
                            {'key': 'HostName', 'value': windowsreply},
                            {'key':'deviceIsOnline', 'value': True},
                            {'key': 'onOffState', 'value': True},
                            {'key': 'deviceTimestamp', 'value': str(t.time())},
                            {'key': 'ipAddress', 'value': str(self.client_address[0])}
                              ]
                    dev.updateStatesOnServer(stateList)
                    #Create device and then return
                    return

            for dev in indigo.devices.itervalues('self.WindowsComputer'):
                if dev.enabled:
                    CPU = 'unknown'
                    if 'CPU' in dictparams:
                        CPU = dictparams['CPU']
                    MemFree = 'unknown'
                    if 'MemLoad' in dictparams:
                        MemFree = dictparams['MemLoad']
                    FGApp = 'unknown'
                    if 'ForeGroundApp' in dictparams:
                        FGApp = dictparams['ForeGroundApp']
                    MACaddress = ''
                    if 'MAC' in dictparams:
                        MACaddress = dictparams['MAC']
                    idletime = 0
                    if 'Idle' in dictparams:
                        idletime = dictparams['Idle']
                    userName = 'unknown'
                    if 'userName' in dictparams:
                        userName = dictparams['userName']
                    upTime = 0
                    if 'upTime' in dictparams:
                        upTime = dictparams['upTime']
                    version = 'unknown'
                    if 'version' in dictparams:
                        version = dictparams['version']

                    if dev.states['HostName']== dictparams['Hostname']:
                        #dev.updateStateOnServer('deviceIsOnline', value=True)
                    # self.createupdatevariable(dev.states['optionValue'], 'False')
                        stateList = [
                            {'key': 'cpu', 'value': CPU},
                            {'key': 'memFree', 'value': MemFree},
                            {'key': 'foregroundApp', 'value': FGApp},
                            {'key': 'ipAddress', 'value': str(self.client_address[0])},
                            {'key': 'deviceIsOnline', 'value': True},
                            {'key': 'deviceTimestamp', 'value':str(t.time())},
                            {'key': 'onOffState', 'value': True},
                            {'key': 'MACaddress', 'value': MACaddress},
                            {'key': 'idleTime', 'value': idletime},
                            {'key': 'userName', 'value': userName},
                            {'key': 'WindowsVersion', 'value': version},
                            {'key': 'upTime', 'value': upTime}
                        ]
                        dev.updateStatesOnServer(stateList)


        except:
            self.plugin.logger.exception(u'Exception in do_POST single thread.')
            return



