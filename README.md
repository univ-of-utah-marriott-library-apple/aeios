# AEiOS (Automated Enterprise iOS)

A python library designed to aid the automation of Apple iOS device management, configuration and imaging.

# Goal
Specifically designed for our in-house *Student Checkout iPads*, we wanted to provide our students and patrons the ability to use our iPads *without restrictions*.

Our iPads can be (and often are) used as if they were personal devices. Users can configure the devices however they like, install their own applications, and even use iCloud, while also maintaining *User Data Privacy* between each checkout.


By integrating the best features of Apple's "Apple Configurator 2", Device Enrollment Program (DEP), and Mobile Device Management (MDM). We have created a completely automated, and **truly** zero-touch solution for iOS device checkout using free and native Apple macOS solutions.

Now it’s time to share :)

---

# Setup and Configuration


### First Steps

Make sure you have [Apple Configurator 2](https://itunes.apple.com/us/app/apple-configurator-2/id1037126344) installed as well as its [automation tools](https://support.apple.com/guide/apple-configurator-2/command-line-tool-installation-cad856a8ea58). `AEiOS` will not be able to perform any tasks without these tools installed.

### Configuration

Because device automation is enterprise specific, `AEiOS` will need some site specific configuration before automation will work properly. It comes with a tool designed for just that purpose called `aeiosutil`.

Here is an example of general configuration:
```bash
$ aeiosutil add wifi </path/to/wifi.mobileconfig>
$ aeiosutil add identity --p12 </path/to/supervision.p12>
$ aeiosutil add image --background </path/to/background.png>
$ aeiosutil configure slack "https://slack.webhook" "#aeios-channel"
$ aeiosutil add app "Microsoft Word"
$ aeiosutil add app "Google Docs: Sync, Share, Edit"
$ aeiosutil start
```

Most configuration will be a one-time process, but as you need to update various parts (i.e. automate new apps/remove old apps, change backgrounds, different wifi, etc.) `aeiosutil` will be your go-to tool.


### Usage

Each sub-command for `aeiosutil` has it's own help page, as do most of the arguments themselves. All of the following commands will provide different help pages:
```bash
$ aeiosutil --help
$ aeiosutil add --help
$ aeiosutil add identity --help
```

### Wi-Fi Profile

A working Wi-Fi profile is necessary for [DEP Re-Enrollment](#device-supervision), and can be added via:
```bash
$ aeiosutil add wifi /path/to/wifi.mobileconfig
```

Be sure to test your wifi profile before adding it to `AEiOS`. The wifi profile can be removed via:
```bash
$ aeiosutil remove wifi
```


### Supervision Identity

Some automated actions can only be performed on supervised devices (specifically [Custom Backgrounds](#custom-backgrounds), and [Load Balancing](#load-balancing)). These actions will necessitate `AEiOS` to have  access to the same supervision identity used to manage the device in your MDM.

Your MDM should have a mechanism for exporting your supervision identity used for your DEP. If you've already added your supervision identity to Apple Configurator, it can be [exported](https://support.apple.com/en-us/HT207434) from there. Once exported it can be added one of two ways:

Import password protected pkcs:
```bash
$ aeiosutil add identity --p12 /path/to/supervision_identity.p12
```

Import unencrypted supervision identity certificates:
```bash
$ aeiosutil add identity --certs /path/to/exported/certs/directory
```

Importing your supervision identity is not required for `AEiOS` to automate [Resetting Devices](#erasing-devices), [DEP Re-Enrollment](#device-supervision), or [VPP App Installation](#vpp-app-installation).


### Custom Backgrounds

Once all automation and verification is completed, `AEiOS` will set the Lock and Home screen with an image of your choosing, if provided.

Add custom background image:
```bash
$ aeiosutil add image --background /path/to/image
```

Setting the background requires the device to be supervised and an imported [supervision identity](#supervision-identity). Unsupervised devices will skip this step.


### Reporting

In order to keep your library of apps up-to-date and relevant, any apps installed on devices outside of `AEiOS` will be reported as they are encountered. Reporting is handled via [Slack Incoming Webhooks](https://api.slack.com/incoming-webhooks). 

It can be configured via:
```bash
$ aeiosutil configure slack 'https://slack.webhook.url' '#channel-name' 
```

Additionally, critical errors with automation that require attention will also be reported to Slack.


## Automating Application Installation

All iOS app installation is done using Apple Configurator 2 GUI. You'll need to have VPP apps purchased and available for `AEiOS` to be able to automatically install them.

In Apple Configurator 2:

    1. View > List > Add UDID column
    2. Sign into your VPP account
    3. Specify apps to automatically install


### Configuring App Installation

`aeiosutil` can be used to specify apps to be installed during automation. Each app has to be added via its iTunes name (Apple Configurator 2 > Actions Menu > Add > Apps… > "Name" column). You'll be prompted for Accessibility Access the first time apps are Installed (see [VPP App Installation](#vpp-app-installation)).

The app name has to be added **exactly** as it appears in Apple Configurator. Be sure you have enough available licenses for all of your devices.


Adding apps:
```bash
$ aeiosutil add app "Microsoft Word"
$ aeiosutil add app "Google Docs: Sync, Share, Edit"
```

Removing apps:
```bash
$ aeiosutil remove app "Microsoft Word"
```

Additional help:
```bash
$ aeiosutil add app --help
$ aeiosutil remove app --help
```


## Running Automation

Starting automation:
```bash
$ aeiosutil start
```

Stopping automation:
```bash
$ aeiosutil stop
```

Start `AEiOS` automatically at login:
```bash
$ aeiosutil start --login
```

Stop `AEiOS` from automatically running at login:
```bash
$ aeiosutil stop --login
```


# Under The Hood

AEiOS essentially performs 6 tasks:

    1. Erase
    2. Re-Enroll via DEP
    3. Install VPP Apps (optional)
    4. Customization (optional)
    5. Verification
    6. Load Balancing

 
## Erasing Devices

When an iOS device is connected for the first time to a Mac system running `AEiOS`, you will be given following choices:

    A) Enable automation for the device which will cause it to be automatically
       erased each time it is connected to the system,
    B) Ignore the device and permanently exclude it from automation.
    C) Cancel
    
Currently, the "Ignore" and "Erase" options are not configurable apart from this first prompt. This will probably change in the near future.

If you select "Cancel", you'll be re-prompted each time this device connects until another choice is made. 

### WARNING

If you selected "Erase" incorrectly, and it erases a device, it cannot be undone... ¯\\\_(ツ)_/¯

However, if you've accidentally ignored a device you want automated you can always reset AEiOS to a default state (see [Troubleshooting](#troubleshooting))


## Device Supervision

Device supervision is handled via DEP, and while it's *technically* not required, I'm not sure how gracefully `AEiOS` handles non-DEP devices (see [Intentionally Unsupervised Devices](#Intentionally-unsupervised-devices)). If this is proves problematic in your environment, submit a bug, and I'll do my best to integrate non-DEP supervision and/or non-supervised device automation. 

Because DEP Enrollment requires iOS device network, DEP Re-enrollment and device supervision cannot be done without a [Wi-Fi profile](#wi-fi-profile).

Though I put a lot of work to integrate Tethered-Caching as an alternative network mechanism, Apple has refused to support iOS device tethering since releasing iOS 12. I could rant and complain (in detail), but it's not going to change the fact that it's currently inoperable. I've included the tethering library in `AEiOS`, but it doesn't really do much.

Enabling "Content Caching" in System Preferences > Sharing will lessen the load on your network for App installation, but a working Wi-Fi profile is still required. 

If the Wi-Fi Profile works, via MDM or Apple Configurator 2, it will work with `AEiOS` and because DEP only requires a device to have network connectivity for few seconds, I suggest setting the profile to automatically remove itself, but hey... do whatever.


## VPP App Installation

Because of inconsistencies with "Best Effort" MDM app installation, and instability with iOS device tethering, `AEiOS` automates the installation of VPP apps via the Apple Configurator 2 GUI. There is not currently a (viably configurable) way to manually install VPP apps other than with the Apple Configurator GUI.

However, utilizing System Events comes with baggage... namely Accessibility Access. 

With known exploits, Apple is particularly sensitive about granting Accessibility Access to anything that asks, but it's also not very consistant with how Accessibility Access is handled. As far as I can tell, any script executed by `cfgutil` (Apple's own automation tool) executes scripts directly from `/bin/sh`, which means it *needs* Accessibility Access in order for the GUI automation to work. Congratulations Apple! youplayedyourself.gif

I have figured out a way to circumvent giving Accessibility Access to `/bin/sh`, but it is going to require some significant refactoring, and will not be included in the initial release.

In this version of `AEiOS`, `checkout_ipads.py` and `sh` will *BOTH* need to be given Accessibility Access for VPP App installation to work. If that's considered too great of an insecurity, VPP App Installation does not need to be implemented via `AEiOS` and you can install apps via other, institutionally applicable mechanisms.

Securing Accessibility Access requirements is my top-most priority, and will be addressed before additional features are released.

While `cfgutil` *does* have an `install-apps` subcommand that would circumvent the need for Accessibility Access altogether, but the catch is that it only works with local .ipa files. As far as I can tell, Apple has removed the ability to easily save .ipa files locally on a system, however, even with local .ipa's, `cfgutil` lacks the ability to assign VPP app licenses, making `install-apps` almost entirely useless.

We've submitted a feature request to update `install-apps` to work with VPP apps, but I'm not holding my breath... If the feature is added though, it will immediately be leveraged and integrated into `AEiOS`.

Utilizing Apple Configurator 2 to install apps, means that it comes with some overhead has taken a significant amount of effort to mitigate. That being said, sometimes Apple Configurator 2 just freaks out for no reason...

I've integrated some blanket fault tolerance for the most common issues. (Internal VPP errors, App not available, unable to assign license, etc.), but GUI's are difficult to test, especially when the GUI is someone else's.

I'll be improving app installation as development continues.


### Verification

Due to inherent uncertainty of a device's state (e.g. random disconnects, false checkouts, internal VPP errors, etc.) `AEiOS` has a lot of built-in fault tolerance. I'm constantly surprised how many errors are fixed simply by "trying again with fewer devices", so instead of failing on an error, it just moves along to the next step. 

After any given round of automation is completed, `AEiOS` verifies each device and re-tasks any steps that failed. All verified devices are load-balanced and a smaller subset of tasks are performed.

Due to random intermittent issues with VPP App Installation. App verification is only performed 3 times and failure is reported ([if configured](#reporting)) after a 3rd unsuccessful attempt.


### Load Balancing

A single system tends to get overloaded around 9-10 iOS devices, this causes the USB bus to start acting oddly and as a result, devices can randomly disconnect in the middle of automation, drop all connections when another device is reconnected, or keep devices from connecting to the system at all.

Because VPP accounts can only be tied to one system at a time, you'll either have to have multiple VPP accounts, or limit the number of devices connected to a single system at a time.

To mitigate this issue as much as possible, devices that have successfully completed all automation are shutdown to limit the number of active connections on a single USB bus.

Because there is not (currently) a way to determine if a device was checked out other than it is no longer connected to the system, a device will be re-erased if it is reconnected after being shutdown (for more than 5 minutes).

Load Balancing cannot be performed without supervised devices and an i[mported supervision identity](#supervision-identity).


## CAVEATS

### Apple Configurator UDID Column and Sorting

Devices are identified in the Apple Configurator GUI via the UDID, so if that column is missing, app installation will fail. 

Before running `AEiOS`, make sure the UDID column is present, and used for device sorting. If Apple Configurator is set to sort by device name, and those names are modified during device selection, weird things can happen. Sorting via UDID will keep everything very consistent and keep things running smoothly.


### Intentionally Unsupervised Devices

Device supervision *is* one of the hard-coded verification step in `AEiOS`, so if a device is left unsupervised, it will not be counted "verified" and it will continuously attempt to re-supervise the device.

Although Erase and App installation will still take place if a device is left intentionally unsupervised, custom backgrounds are skipped, and load-balancing cannot take place.

There also maybe issues with 

This may be addressed in a future release.


## Troubleshooting

`AEiOS` is designed to work from scratch, so all `.plist` files located in `~/Library/aeios` can be safely deleted, but you might lose some configuration

If you ever need to simply "reset" `AEiOS`, you can safely run the following command without deleting any existing configuration:

```bash
$ aeiosutil stop
$ find ~/Library/aeios -name "*.plist" -not -name "*apps.plist" -delete
$ aeiosutil start
```

**NOTE**: Don't rely on this one-liner in future releases, but until I add the functionality to `aeiosutil`, the example above is the de-facto, non-destructive way clear everything and start fresh.

**WARNING**: This will also delete all iOS device records, as well as ignored devices, so each device will re-prompt the next time it reconnects to the system and any device that is currently connected to the system will be re-erased.


## Uninstalling

`Uninstall AEiOS.app` is included with the installer, but can also be found in: `/Library/Python/2.7/site-packages/aeios/scripts`.

Alternatively, you can manually run the uninstall script with:
```bash
$ sudo /Library/Python/2.7/site-packages/aeios/scripts/uninstall.sh
```

The uninstaller will remove all trace of `AEiOS` from the system including itself. This includes all user files (e.g. logs, supervision identities, images, profiles, and preferences) so if you want to save them, copy them before-hand.

### Files

I always find myself wanting to know where certain files are kept, so I've made sure to include that information here for those who are interested.

Installed files can be listed via the command-line:
```bash
$ pkgutil --files "edu.utah.mlib.aeios"
```

Most configuration and supporting files are located in: `~/Library/aeios`

           Logs:  ~/Library/aeios/Logs
    LaunchAgent:  ~/Library/LaunchAgents/edu.utah.mlib.aeios.plist
    Preferences:  ~/Library/Preferences/edu.utah.mlib.aeios.plist


All of these files listed above are removed by the uninstaller.


# Contact

Issues/bugs can be reported [here](../../issues). If you have any questions or comments, feel free to [email us](mailto:mlib-its-mac-github@lists.utah.edu).

Thanks!


## Update History

| Date       | Version | Description
|------------|:-------:|------------------------------------------------------|
| 2019-04-24 | 1.0.0   | Initial Release                                      
