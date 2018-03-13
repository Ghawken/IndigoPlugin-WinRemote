# WinRemote Plugin

![](https://github.com/Ghawken/IndigoPlugin-WinRemote/blob/master/WinRemote.indigoPlugin/Contents/Resources/icon.png)

This is a plugin for Indigodomo that aims to create any Windows Computer as a IndigoDomo device.  

This enable status updates within Indigo, the plugin also displays what is the foreground Application on the Windows Computer, CPU, Memory Free etc.  

It also enables Turn Off/Turn On (using WakeonLan) commands as well as custom commands to be sent.

To do this we need two way communication back and forward to indigo.  

This is achieved through running a simple server with this plugin on Indigo and a separate windows tray application to periodically communicate back to the Indigo Server on the Windows PC.

eg.
![](https://image.ibb.co/ntZ5Xn/Tasbar_Icons.png)

(other Windows methods such as WMI communication etc.etc. were trialled but were very difficult to set up in my one case let alone others and I quickly abandoned this approach)

There are two apps - One for Indigo Server, and One for the  Windows Computer - IndigoPlugin Communicator - they both, and all instances communicate through a single port
**This Defaults to port 9123.**

## **Why bother?  Some reasons:**
* Probably most basically - can turn on/turn off windows easily within Indigo/HomeBridge/Alexa.  eg. 'Alexa turn-off Computer name'
* Can Message Windows PC on events as required.  Security triggers, motion, doorbell - can pop up message on Windows PC.
* Can check running Foreground application and trigger timers on these events -eg. to much minecraft, not enough maths-online
* Can check CPU usage/Memory Free and can trigger if issues
* Can display details in Control Page for easy reference


## Setup

To setup install the WinRemote IndigoPlugin on your Indigo Server.  Select the port to use/Defaults to 9123.   This needs to be a free unused port.

For the plugin to work - the Windows Application needs to be able to 'talk' to the Indigo Server on this port.  

Both Indigo Mac and the Windows Computer must allow communication or traffic through firewall on this port.
Open up Firewalls to either this port or this app to allow this.

Once the WinRemote plugin is installed on the Mac.  Enable it if not enabled.

Ideally create a Devices Directory in Indigo Server Called "Windows Computers"

**The Plugin Will Create these Devices as seen for you**

When new Windows Computer devices are created they will be placed here.  
Once created, they can be moved/renamed etc as needed and will not be recreated unless deleted.

The devices are only created either at startup of the IndigoPlugin Communicator app, or when the connect button is pressed.  So if you need to recreate a Indigo Device just re-press connect on the PC Indigo Communicator app.

**Plugin Config**
![](https://image.ibb.co/dZMvq7/Plugin_Config.png)


## On Windows Computer

Run Installer for your version of Windows (32bit or 64bit).  If not sure just use 32bit - not sure there is any practical difference.
The Installer also should create a startup entry so app will run on Startup/log in of that user.

Next run the IndigoPlugin Communicator app.

_This application requires .Net 4.6 installed to run._
_(standard on Windows 10, separate install on some Windows 8)_
_If needed it will prompt for download, download, install and run again.  (doesn't need restart)_

As the Application is not set up will need a few settings need to be entered.

![](https://image.ibb.co/fA18k7/PCWindow.png)

Application should open a window for you to enter you Indigo Server details IP address, and the Port you have set within the Indigo Mac WinRemote Plugin (defaults to 9123)
eg. 
IndigoServer IP - 192.168.1.6  -- Enter your indigoserver IP address
Port - Defaults to 9123 - set with Indigo WinRemote Plugin
e.g if as above Should Enter 192.168.1.6:9123

Once entered press the **Connect Button.**

![](https://image.ibb.co/b5euQ7/PCWindow_Connect.png)

This should connect to running WinRemote Indigo Plugin on Indigo Server
(If any error messages will display below - most likely are failure to connect because of incorrect IP/Ports or firewall based settings.)
Once connected, choose Debug Log options and click Save
(this will be the last time you see this window)

If there are any connection errors will display the error in the Window - fix firewall, ports and try again.,

Now you should see a little indigo icon in the Windows Taskbar.  
See here:
Hover mouse over and you will see connected and the time of last communication.
eg
![](https://image.ibb.co/hohQxn/Taskbar_Windows_Hover.png)

Double click the taskbar icon to make disappear/reappear, or right click on the taskbar icon to Hide Window/Show Window and Exit program.

![](https://image.ibb.co/iBHV3S/taskbar_Right_Click.png)


## Back to Indigo Mac Server

Now on the Mac server within the 'Windows Computers' folder or the main device folder you should see a new 'Windows Computer' Device.

This has the following states

![](https://image.ibb.co/gn5iOS/Device_States.png)


* CPU - Current cpu usage
* ForegroundApp - the Current Application that has focus/is in the Foreground
* MemFree - Memory free
* deviceIsOnline - true/false
* Hostname - Name of the Computer
* IP Address - Current IP Address of the computer
* MACaddress - the MAC address of the Network device communicating with the IndigoServer
* pendingCommands - list of current pending commands (only one at once is supported)
* WindowsVersion - Verison of Windows including Build and updates currently running
* UserName - User name of logged in User
* idleTime - time the the computer has not had any user input keyboard/mouse measured in Minutes
* upTime - time the system has been running for measured in hours

_(some of these settings take a few minutes to be calculated, pulled, particularly the MAC address)_

## Device Settings

There is only one setting which is as below.  If this is checked the Computer will ignore any Turn-Off Commands sent to it.  This is to avoid accidentally turning off.

![](https://image.ibb.co/mdtx3S/Device_Settings.png)


## Actions

![](https://image.ibb.co/b8Xmcn/Action_States.png)

### Turn On/Turn Off/Restart

You will notice there is also a Turn On/Turn Off button control for this new Windows Computer.
This is also duplicated in a Action Group for Turn-On/Turn-Off

This will Turn-Off the selected computer within 10seconds with a 10 second warning.

Turn-On uses the MacAddress to send a Wake-On-Lan signal to that computer.
(The computer must be able to response to WOL signals which require sometimes BIOS settings/Windows Network Settings changes)

**Other Actions include**
### Send Message 
this will pop up and Send Message to the selected Computer(s)

e.g 
Windows 8  

![](https://image.ibb.co/dA2Eq7/Windows_Msg_Win8.png)
Windows 10

![](https://image.ibb.co/mXyok7/Windows10_Message.png)

### Lock Computer

Return the Computer to the log in screen - leaving user logged in

### Run Process

This can run any process on the Windows PC that the logged in User has access to. e.g. Notepad, chrome, etc.
Select Action Group, Select Computer (can send same command to multiple computers), then enter the process itself. (this will need path if doesn't run without path in cmd.exe)
Then enter any arguments if any required for the process.

eg. Run Windows Defender Scan

![](https://image.ibb.co/eOhJA7/Process_Defender_Scan.png)

eg. Check for Windows Updates
![](https://image.ibb.co/fGxkq7/Process_Update_Windows.png)

eg. Run CCCleaner in automatic mode
![](https://image.ibb.co/e5EciS/Run_Process.png)


If there is any security concern about this - it does allow Indigo to run any process on that PC (that the user has access to) 
This can be completely disabled within the Main Window. With Checking the Disable Process Commands Checkbox (this will not disable other set commands) (If someone has access to your network, this specific port even inside or outside, and can run the commands I believe you have bigger problems - but none-the-less this option is here)

![](https://image.ibb.co/cGcoOS/PCWindow.png)

The message and the commands (with exception of Turn-On) will be sent at the next communication (every 60 seconds)







