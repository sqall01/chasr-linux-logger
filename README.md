![ChasR Logo](img/chasr_logo_black.png)

[ChasR is an open-source end-to-end encrypted GPS tracking system](https://alertr.de/chasr). It can be used directly as [service](https://alertr.de/chasr) or hosted by oneself. The goal of ChasR is to offer a privacy protecting GPS tracking service by using end-to-end encryption. This means that the sensitive location data of a user is directly encrypted on the device before it is sent to the server. Since the server does not know the key for the encryption, it cannot see the location data. The stored location data can be accessed either via Android App or web interface. Again, the location data is decrypted on the device and hence the server has no way of knowing the location of the user. All you need to use ChasR is a [free account](https://alertr.de/register) and ChasR logging application.

The ChasR GPS Tracking System is separated into multiple components:

**Logger**

* ChasR Android Logger ([Github](https://github.com/sqall01/chasr-android-logger) | [Google Play](https://play.google.com/store/apps/details?id=de.alertr.chasr))
* ChasR Linux Logger ([Github](https://github.com/sqall01/chasr-linux-logger))

**Map**

* ChasR Android Map ([Github](https://github.com/sqall01/chasr-android-map) | [Google Play](https://play.google.com/store/apps/details?id=de.alertr.chasrmap))

**Server**

* ChasR Server ([Github](https://github.com/sqall01/chasr-server) | [Service](https://alertr.de/chasr))

Additionally, the ChasR GPS Tracking System can be used as part of the [AlertR Alarm and Monitoring System](https://alertr.de) (for example as a car alarm system).


# ChasR Linux Logger

This is a Linux logger for the ChasR GPS Tracking System. Its task is to gather the location data, encrypt it locally on the device and submit it to the ChasR server. It is written in Python3 and uses the gpsd provided on most Linux distributions.

A picture of a temporary test logging setting with a Raspberry Pi:
![Raspberry Pi Setting](img/pi_setting.jpg)

## Install

Installing the Linux logger is rather simple. All it needs is Python3, gpsd and some packages provided via pip. This example shows how to setup the logger on an Ubuntu Linux.

First, the needed packages have to be installed:

```bash
root@towel:~# apt install gpsd python3 python3-pip
```

Next the gpsd has to be configured. I used an USB GPS dongle for it. This dongle was registered as device under `/dev/ttyACM0`. The configuration file under Ubuntu is located at `/etc/default/gpsd` and looked like the following:

```bash
# Start the gpsd daemon automatically at boot time
START_DAEMON="true"

# Use USB hotplugging to add new USB devices automatically to the daemon
USBAUTO="true"

# Devices gpsd should collect to at boot time.
# They need to be read/writeable, either by user gpsd or the group dialout.
DEVICES="/dev/ttyACM0"

# Other options you want to pass to gpsd
GPSD_OPTIONS=""
```

The Linux logger needs furthermore some packages provided by pip, which can be installed via the following command:

```bash
root@towel:~# pip3 install requests
root@towel:~# pip3 install gps3
root@towel:~# pip3 install pycrypto
```

Next the ChasR Linux Logger has to be configured. Rename the configuration template file `config/config.conf.template` to `config/config.conf` and insert the needed information into it. The most important settings that have to be set are the [ChasR username and password](https://alertr.de/register), the secret (which is the key used to encrypt the GPS data) and the device name.

Afterwards, you can start the logger to track your location by executing:

```bash
sqall@towel:~/chasr-linux-logger$ ./chasr.py 
```


# Supporting ChasR
<a name="supporting_chasr"/>

If you like this project you can help to support it by contributing to it. You can contribute by writing tutorials, creating and documenting exciting new ideas to use ChasR (for example on [the AlertR subreddit](https://www.reddit.com/r/AlertR/)), writing code for it, and so on.

If you do not know how to do any of it or do not have the time, you can support the project by [donating](https://alertr.de/donations.php) or support me on [Patreon](https://www.patreon.com/sqall). Since the service has a monthly upkeep, the donation helps to keep these services free for everyone.

### Patreon
[![Patreon](https://c5.patreon.com/external/logo/become_a_patron_button.png)](https://www.patreon.com/sqall)

### Paypal
[![Donate](https://www.paypalobjects.com/en_US/DE/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=TVHGG76JVCSGC)


# Bugs and Feedback
<a name="bugs_and_feedback"/>

For questions, bugs and discussion please use the Github issues.