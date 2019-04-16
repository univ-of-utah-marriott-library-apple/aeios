aeiOS (Automated Enterprise iOS)
---

a library designed to aid the automation of Apple iOS device configuration.

# Goal
Specifically designed for our in-house /Student Checkout iPads/, we wanted to provide our students and patrons the ability to use our iPads *without restrictions*.\* 

Our iPads can be (and often are) used as if they were personal devices. Users can configure the devices however they like, install their own applications, and even use iCloud, while also maintaining /User Data Privacy/ between each checkout.

\*We only restrict iOS Software Updates (to maintain stability), and MDM Profile removal.

By integrating the best features of Apple’s “Apple Configurator 2”, DEP, and MDM. We have created a completely automated, and *Truly Zero-Touch* solution for iOS device checkout using free and native Apple macOS solutions.

Now it’s time to share :)
# Setup

Basic: Erase & MDM/DEP Re-enrollment (no Apps)
    1. Install Apple Configurator 2 > Automation Tools...
    2. Add Wi-Fi Profile:
        `$ aeiosutil add wifi </path/to/wifi.mobileconfig>`


VPP Apps:

Apple Configurator 2

    1. View > List > Add UDID and ECID column (sort by ECID)
    2. Sign into VPP account
    Optional:
    Apple Configurator 2 Preferences... Organizations > Add Organization


Background:
    `$ aeiosutil add image --background </path/to/image>`

Reporting:
    `$ aeiosutil configure slack URL CHANNEL`


---
## Workflow

aeiOS essentially performs 5 tasks:

    1. Erase
    2. Re-Enroll via DEP
    3. Install VPP Apps (optional)
    4. Customization (optional)
    5. Verification
    
### Erasing Devices

When an iOS device is connected for the first time to a system running `aeiOS`, you will be given following choice, either:

    A) Enable automation for the device which will cause it to be automatically
       erased each time it is connected to the system,
    B) Ignore the device and permanently exclude it from automation.
    C) Cancel
    
Currently, Ignore and Erase are not configurable apart from this first prompt. (this will probably change in the near future.)

If you select "Cancel", you'll be re-prompted each time this device connects until another choice is made. 

If you selected "Erase" incorrectly, it cannot be undone... ¯\_(ツ)_/¯

However, if you've accidentally ignored a device you want automated you can always reset aeiOS to a default state (see "Troubleshooting")


### Device Supervision

Device supervision is handled via DEP, and while it's /technically/ not required, I'm not sure how gracefully `aeiOS` handles non-DEP devices. (See "Un-Supervised Devices" in CAVEATS) If this is proves problematic in your environment, submit a bug, and I'll do my best to integrate non-DEP supervision and/or non-supervised device automation. 

Because DEP Enrollment requires iOS device network, DEP Re-enrollment and device supervision cannot be done without a Wi-Fi profile.

Though I put a lot of work to integrate Tethered-Caching as an alternative network mechanism, Apple has refused to support iOS device tethering since releasing iOS 12. I could rant and complain (in detail), but it's not going to change the fact that it's currently inoperable. I've included the tethering library in `aeiOS`, but it doesn't really do much.

Enabling "Content Caching" in System Preferences > Sharing will lessen the load on your network for App installation, but a working Wi-Fi profile is still required, your Wi-Fi profile can be added to `aeiOS` with the following command:

```bash
$ aeiosutil add wifi /path/to/wifi.mobileconfig
```

If the Wi-Fi Profile works, via MDM or Apple Configurator 2, it will work with `aeiOS` and because DEP only requires a device to have network connectivity for few seconds, I suggest setting the profile to automatically remove itself, but hey... do whatever.


### VPP App Installation

Because of inconsistencies with "Best Effort" MDM app installation, and instability with iOS device tethering, `aeiOS` automates the installation of VPP apps via the Apple Configurator 2 GUI. There is not currently a (viably configurable) way to manually install VPP apps other than with Apple Configurator 2's GUI. (see `rant` below)

However, utilizing System Events comes with baggage... namely Accessibility Access. 

With known exploits, Apple is particularly sensitive about granting Accessibility Access to anything that asks, but it's also not very consistant with how Accessibility Access is handled. As far as I can tell, any script executed by `cfgutil` (Apple's own automation tool) executes scripts directly from `/bin/sh`, which means `/bin/sh` *needs* Accessibility Access for the GUI automation to work. Congratulations Apple! youplayedyourself.gif

I *HAVE* figured out a way to circumvent giving access to `/bin/sh` with LaunchD, but is going to require some significant refactoring.

In this version of `aeiOS`, `checkout_ipads.py` and `sh` will *BOTH* need to be given Accessibility Access for VPP App installation to work. If that's considered too great of an insecurity, VPP App Installation does not need to be implemented via `aeiOS` and you can install apps via other, institutionally applicable mechanisms.

Securing Accessibility Access requirements is my top-most priority, and will be addressed before additional features are released.

```html
<rant>
While `cfgutil` DOES have an `install-apps` subcommand, it only works with local .ipa files, and Apple has removed the ability to (easily) save .ipa files locally on a system, (there's also no way in license VPP apps with `cfgutil`, so it doesn't matter much anyway).

We've submitted a feature request, but I'm not holding my breath...
</rant>
```

Utilizing Apple Configurator 2 to install apps, means that it comes with some overhead that I have taken sizable effort to mitigate. That being said, sometimes Apple Configurator 2 just freaks out for no reason what-so-ever.

I've integrated some blanket fault tolerance for the most common issues. (Internal VPP errors, App not available, unable to assign license, etc.), but GUI's are difficult to test, especially when the GUI is someone else's.

I'll be improving this portion as well as development continues.

#### Adding Apps

Apps have to be added to automation via their iTunes Name (as it appears in Apple Configurator 2 under the "Name" column) and can be done via the command:

```bash
$ aeiosutil add app "Microsoft Word"
```

Be sure you have enough licenses for all of your devices before adding an app to the automation, I'm not sure exactly how it will be handled.


### Customization

#### Backgrounds

Custom backgrounds can only be set on supervised devices and need the correct supervision identity to be modified. Export your MDM's existing supervision identity (either directly from the MDM, or from Apple Configurator 2). Once exported it can be added to `aeiOS` via `aeiosutil` with either of the following commands

```bash
$ aeiosutil add identity --p12 /path/to/supervision_identity.p12
```

Or, if you export your supervision identity via Apple Configurator 2

```bash
$ aeiosutil add identity --certs /path/to/exported/certs/directory
```

Your customized background can be added with the following:

```bash
$ aeiosutil add image --background /path/to/image
```

The order of these commands doesn't matter.

More customization will be included in future releases


## Reporting

In order to keep your library of apps up-to-date and relevant, any apps installed on devices that aren't automatically installed (or known by) `aeiOS` will be reported as they are encountered 
Reporting is handled via Slack Webhook {site} and can be configured:

```bash
$ aeiosutil configure slack https://slack.webhook.url '#channel-name' 
```

Additionally, critical errors to the automation that require attention will also be reported.

## Configuration:

Most configuration is done with `/usr/local/bin/aeiosutil` (see `aeiosutil --help` for more information).

General configuration will go something along the lines of this:

```bash
$ aeiosutil add wifi </path/to/wifi.mobileconfig>
$ aeiosutil add identity --p12 </path/to/supervision.p12>
$ aeiosutil add image --background </path/to/background.png>
$ aeiosutil configure slack "https://slack.webhook" "#aeios-channel"
$ aeiosutil add app "Microsoft Word"
$ aeiosutil add app "Microsoft Excel"
$ aeiosutil add app "Microsoft PowerPoint"
```

And as long as Apple Configurator 2 has the UDID column and is setup with a VPP account with enough licences for all of the devices. You're done!

Single apps can be removed from automation with the following:

```bash
$ aeiosutil remove app "Microsoft Word"
```

Each sub-command for `aeiosutil` has it's own help page, and most arguments for each sub-command do as well.

```bash
$ aeiosutil --help
$ aeiosutil add --help
$ aeiosutil add app --help
```

## CAVEATS

### Load balancing

A single system tends to get overloaded around 9-10 iOS devices, this causes the USB bus to start acting oddly and can cause devices to randomly disconnect in the middle of automation or keep devices from connecting to the system at all.

Because VPP accounts can only be tied to one system at a time, you'll either have to have multiple VPP accounts, or limit the number of devices connected to a single system at a time.

To mitigate this issue as much as possible, devices that have successfully completed all automation are shutdown to limit the number of connections on a single USB bus.

Because there is not (currently) a way to determine if a device was checked out other than it is no longer connected to the system, a device will be re-erased if it is reconnected after being shutdown (for more than 5 minutes).


### Intentionally Unsupervised Devices

Checking device supervision *is* one of the hard-coded verification step in `aeiOS`, so if a device is left (supervised, it will not be counted as verified and it will continually attempt to re-supervise the device.

Although, Erase and App installation will still take place if a device supervision fail, unsupervised devices will never be "verified", so load-balancing will not take place. 

This will be addressed in a future release

---
## Troubleshooting

`aeiOS` is designed to work from scratch, so all `.plist` files located in `~/Library/aeios` can be safely deleted, but you might lose some configuration

If you ever need to simply "reset" `aeiOS`, you can safely run the following command without deleting any existing configuration:

```bash
$ find ~/Library/aeios -name "*.plist" -not -name "*apps.plist" -exec rm
```

NOTE: Don't rely on this one-liner in future releases, but until I flush out `aeiosutil`, it's currently the least damaging way to simply clear everything and start fresh.

This will also delete all iOS device records, as well as ignored devices, so each device will re-prompt the next time it reconnects to the system and any device that is currently connected to the system will be re-erased.

Additional preferences can be found in: `~/Library/Preferences/edu.utah.mlib.aeios.plist`

