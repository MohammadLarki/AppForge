# Building the AppForge Debian package

AppForge's desktop release targets Ubuntu 22.04+ and Debian 12+ with Python
3.10 or newer. Fedora, Arch, and other distributions are not supported by this
package yet.

## Build dependencies

On a Debian or Ubuntu build machine, install the build tools:

```bash
sudo apt update
sudo apt install debhelper devscripts
```

These tools are only needed to build the package. The generated package needs
only the distribution `python3` and `python3-tk` packages at runtime.

## Build

From a clean checkout:

```bash
export SOURCE_DATE_EPOCH=1700000000
dpkg-buildpackage -us -uc -b
```

The package is written one directory above the checkout as
`appforge_0.1.0-1_all.deb`. `SOURCE_DATE_EPOCH` makes the build timestamp
deterministic for reproducible builds.

## Verify package contents

```bash
dpkg-deb -I ../appforge_0.1.0-1_all.deb
dpkg-deb -c ../appforge_0.1.0-1_all.deb
```

The package contains the AppForge modules in `/usr/lib/appforge`, the desktop
launcher in `/usr/share/applications/appforge.desktop`, its icon in the
standard hicolor icon location, and a system launcher at `/usr/bin/appforge`.

## Install and remove

```bash
sudo apt install ../appforge_0.1.0-1_all.deb
sudo apt remove appforge
```

After installation, open **AppForge** from the Applications menu. No virtual
environment, pip command, or terminal is needed to run the installed app.
