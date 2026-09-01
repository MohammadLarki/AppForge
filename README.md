# AppForge

AppForge is a lightweight Linux application installer for Ubuntu and Debian.
It installs `.tar.gz`, `.AppImage`, and `.deb` applications, creates desktop
launchers, and records user-level installations for later removal.

## Supported packages

- AppImage: copied into the current user's local AppForge folder, marked
  executable, and given an application-menu launcher.
- tar.gz / tgz: safely extracted into the current user's local AppForge folder
  and given a launcher when an executable is detected. Electron archives have
  their application icon extracted from `app.asar` when necessary.
- deb: installed system-wide with `apt-get`; the desktop requests an
  administrator password through the operating system.

## Install and run

### Ubuntu and Debian desktop package (recommended)

Download the `appforge_0.1.0-1_all.deb` release and open it in your software
installer, or install it with your package manager. It installs AppForge in the
Applications menu with all required runtime dependencies; you do not need pip,
a virtual environment, or terminal commands to launch it.

To remove AppForge, use your normal software manager or run `sudo apt remove
appforge`. See [the Debian packaging guide](docs/debian-packaging.md) for
building and verifying a package from source.

### Python dependencies

AppForge has no third-party runtime dependencies. To install the project from
a checkout, use a virtual environment and your preferred Python version:

    python -m pip install -e .

For development and tests, install the declared test dependency:

    python -m pip install -r requirements.txt

### System dependency: Tkinter (Ubuntu and Debian)

The desktop interface uses Tkinter. It is supplied by the operating system,
not by pip. Install it before starting AppForge:

    sudo apt update
    sudo apt install python3-tk

When using a separately packaged Python version, install the matching package;
for example, Python 3.14 may need `python3.14-tk`.

Then launch the application:

    python -m appforge

or, after installation:

    appforge

If Tkinter is missing, AppForge prints this guidance rather than a Python
traceback. The GUI also needs a graphical desktop session with a display; it
cannot open in a headless terminal.

## Safety model

- Archive detection and extraction reject unsafe paths and special-file links.
- The UI displays installation failures rather than silently ignoring them.
- AppImage and archive installation remains in the user's home folder by
  default.
- Only `.deb` installation needs elevation, delegated to `pkexec apt-get`.
- User-scope installations are recorded and can be removed from the GUI;
  uninstall removes only the recorded AppForge application directory, launcher,
  and registry entry.

## Planned support

- Automatic icon discovery and extraction
- Electron/Chromium sandbox configuration
- Richer desktop metadata

## License

MIT
