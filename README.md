# student-checkout-ipads

Code to automate the erase, enrollment, and installation of VPP apps on iPads

# running tests
Test can be run using the following `python -m unittest discover ipadmanager`


# aeiOS (Automated Enterprise iOS)
aeiOS is a library designed to aid the automation of Apple iOS device configuration.

Apple iOS devices.
erase, supervision, and app installation for Apple iOS devices

## Dependencies
 - Apple Configurator 2
 - macOS 10.12+
 - management_tools (hopefully removed soon)
 - Apple Volume Purchase Program (VPP)*
 - Apple Device Enrollment Program (DEP)*
 

## Setup
Most of setup involves performing one-time task necessary for the automation of all other tasks
 - Apple Configurator 2
   - install automation tools
   - 2 additional columns: UDID, ECID
   - VPP Account sign in
 - Accessibility Access
   - `/bin/sh`
   - `/Library/Scripts/iPads/ipad_checkout.py`
 - 

## Configuration
Modular configuration isn't completely flushed out

## Reporting
Currently, only supported reporting mechanism is via Slack's [Incoming Webhook](https://api.slack.com/incoming-webhooks)

## Caveats

### Activation Lock
Disabling activation lock is dependent on MDM support

## iOS Device Network
In order for DEP (re-)enrollment to occur, each device must have it's own network connection
By default, this is handled via tethered-caching in 10.12 and Content Caching in 10.13+ 

### Wi-Fi
To use Wi-Fi for iOS Device Network you must create your own .mobileconfig with a Wi-Fi payload
(not fully supported)

#### 10.12
macOS Sierra uses tethered-caching which requires some setup of its own
 - tethered-caching
   - tethered-caching requires root privileges for commands to run without requiring the password run the following command:    
   > ```sudo echo "`whoami` ALL=NOPASSWD: /usr/bin/tethered-caching' > /etc/sudoers.d/tethered_caching```
      
   - The first time tethered-caching runs, it requires user interaction to accept the EULA

 - System Preferences > Network
   - Each device needs a network service defined
   - Using the name of each device as the service name is highly suggested (especially for troubleshooting)

#### 10.13+
macOS High Sierra and Mojave do not include `/usr/bin/tethered-caching` and use Content Caching instead
 - System Preferences > Sharing > Content Caching
   - Share Internet Connection



`id -nu {id}`
   
