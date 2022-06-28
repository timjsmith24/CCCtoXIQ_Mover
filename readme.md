# Centralized to XIQ Mover
## Centralized-to-XIQ-Mover.py
### Purpose
This script will check a /24 subnet for devices that have port 22 open. If the port is open, the script will try and log in with the default Extreme Centralized AP (identify) credentials. If the device can be logged into, the script will check the version and the prompt of the device. If the device is running a later version of software, the script will convert the AP into xiq-cloud operation mode.

### User Input
The subnet that is to be scanned will need to be entered on line 10 of the script. Just the first 3 octets should be entered. The script will check all available ip addresses within the /24 space.

Line 10
```
subnet = "10.128.4"
```
### Requirements
Python 3.6 or higher is recommended for this script.
The python paramiko module will need to be installed. If pip is installed, this can be done with pip install requests. 
The needed modules are listed in the requirements.txt file and can be installed from there.
