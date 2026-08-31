# AppForge

AppForge is a lightweight Linux application installer. Its first MVP focuses on
reliably identifying packages before installation work begins.

## Supported package formats

- .AppImage
- .deb
- .tar.gz and .tgz archives that contain an executable file

## Usage

    from appforge import detect_package

    package = detect_package("~/Downloads/example.tar.gz")
    if package.supported:
        print(package.kind, package.executable)

Archive inspection is read-only: AppForge does not extract files while
detecting the package. Installer, launcher, and icon setup components are the
next milestones.
