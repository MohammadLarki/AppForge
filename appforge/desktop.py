"""Modern Tkinter desktop interface for AppForge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from .detector import PackageKind, detect_package
from .gui import DEVELOPER_LINKS
from .installer import InstallScope, InstallationPlan, create_install_plan
from .registry import RegisteredInstallation, install_and_record, list_installations, uninstall


@dataclass(frozen=True)
class PackageDetails:
    """Presentation-ready information about a selected package."""

    title: str
    package_type: str
    scope: str
    destination: str


def package_details(path: str | Path) -> PackageDetails:
    """Describe a supported package without changing the file system."""
    package = detect_package(path)
    if not package.supported:
        raise ValueError("Choose a supported Linux package.")
    scope = InstallScope.SYSTEM if package.kind is PackageKind.DEB else InstallScope.USER
    plan = create_install_plan(package.path, scope=scope)
    label = {PackageKind.APPIMAGE: "AppImage", PackageKind.DEB: "Debian package", PackageKind.TAR_GZ: "tar.gz archive"}[package.kind]
    return PackageDetails(package.path.name, label, "System-wide" if scope is InstallScope.SYSTEM else "Just for you", str(plan.install_directory))


class AppForgeWindow(tk.Frame):
    """A card-based Linux installer interface backed by AppForge's core APIs."""

    background = "#11131a"
    card = "#1a1e29"
    card_alt = "#222837"
    border = "#30394e"
    text = "#f5f7fb"
    muted = "#9ba7bd"
    accent = "#7c5cff"
    accent_hover = "#947cff"
    success = "#49d17d"
    danger = "#ff6e7c"

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, bg=self.background)
        self.root = root
        self.selected_path: Path | None = None
        self.details: PackageDetails | None = None
        self.status = tk.StringVar(value="Ready for a package")
        self.status_tone = tk.StringVar(value="idle")
        self.path_label = tk.StringVar(value="Drop a package here or choose a file")
        self.package_meta = tk.StringVar(value="Supported: AppImage, tar.gz, tgz, deb")
        self._configure_root()
        self._build_styles()
        self._build_layout()
        self.refresh_installations()
        self._enable_optional_drop_target()

    def _configure_root(self) -> None:
        self.root.title("AppForge · Linux application installer")
        self.root.minsize(760, 580)
        self.root.configure(bg=self.background)
        self.pack(fill=tk.BOTH, expand=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Accent.TButton", background=self.accent, foreground="white", borderwidth=0, padding=(16, 10), font=("TkDefaultFont", 10, "bold"))
        style.map("Accent.TButton", background=[("active", self.accent_hover), ("disabled", "#3c4051")])
        style.configure("Quiet.TButton", background=self.card_alt, foreground=self.text, borderwidth=0, padding=(12, 8))
        style.map("Quiet.TButton", background=[("active", self.border)])
        style.configure("Danger.TButton", background="#3b2630", foreground="#ffb4be", borderwidth=0, padding=(10, 7))
        style.map("Danger.TButton", background=[("active", "#5a2c39")])
        style.configure("App.Horizontal.TProgressbar", troughcolor=self.card_alt, background=self.accent, bordercolor=self.card_alt, lightcolor=self.accent, darkcolor=self.accent)

    def _build_layout(self) -> None:
        shell = tk.Frame(self, bg=self.background, padx=28, pady=24)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=3, minsize=440)
        shell.columnconfigure(1, weight=2, minsize=280)
        shell.rowconfigure(1, weight=1)

        self._header(shell).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        left = tk.Frame(shell, bg=self.background)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        left.columnconfigure(0, weight=1)
        right = tk.Frame(shell, bg=self.background)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self._drop_zone(left).grid(row=0, column=0, sticky="ew")
        self._details_card(left).grid(row=1, column=0, sticky="ew", pady=(16, 0))
        self._status_card(left).grid(row=2, column=0, sticky="ew", pady=(16, 0))
        self._developer_card(left).grid(row=3, column=0, sticky="ew", pady=(16, 0))
        self._installed_card(right).grid(row=0, column=0, sticky="nsew")

    def _header(self, parent: tk.Misc) -> tk.Frame:
        frame = tk.Frame(parent, bg=self.background)
        frame.columnconfigure(0, weight=1)
        tk.Label(frame, text="✦  AppForge", bg=self.background, fg=self.text, font=("TkDefaultFont", 21, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(frame, text="Install and keep your Linux apps tidy", bg=self.background, fg=self.muted, font=("TkDefaultFont", 10)).grid(row=1, column=0, sticky="w", pady=(3, 0))
        tk.Label(frame, text="LOCAL INSTALLER", bg="#25213f", fg="#c9beff", padx=10, pady=5, font=("TkDefaultFont", 8, "bold")).grid(row=0, column=1, rowspan=2, sticky="e")
        return frame

    def _card(self, parent: tk.Misc, **kwargs: object) -> tk.Frame:
        return tk.Frame(parent, bg=self.card, highlightbackground=self.border, highlightthickness=1, padx=18, pady=16, **kwargs)

    def _drop_zone(self, parent: tk.Misc) -> tk.Frame:
        self.drop_zone = tk.Frame(parent, bg="#202538", highlightbackground=self.accent, highlightthickness=1, padx=20, pady=24, cursor="hand2")
        self.drop_zone.columnconfigure(0, weight=1)
        tk.Label(self.drop_zone, text="⇩", bg="#202538", fg="#c9beff", font=("TkDefaultFont", 28)).grid(row=0, column=0)
        tk.Label(self.drop_zone, textvariable=self.path_label, bg="#202538", fg=self.text, font=("TkDefaultFont", 12, "bold"), wraplength=440, justify="center").grid(row=1, column=0, pady=(5, 3))
        tk.Label(self.drop_zone, textvariable=self.package_meta, bg="#202538", fg=self.muted, font=("TkDefaultFont", 9), wraplength=440, justify="center").grid(row=2, column=0)
        browse_button = ttk.Button(self.drop_zone, text="Choose package", style="Quiet.TButton", command=self.choose_package)
        browse_button.grid(row=3, column=0, pady=(16, 0))
        for widget in (self.drop_zone, *self.drop_zone.winfo_children()[:3]):
            widget.bind("<Button-1>", lambda _event: self.choose_package(), add="+")
        return self.drop_zone

    def _details_card(self, parent: tk.Misc) -> tk.Frame:
        card = self._card(parent)
        card.columnconfigure(1, weight=1)
        tk.Label(card, text="DETECTED APPLICATION", bg=self.card, fg="#b9c3d9", font=("TkDefaultFont", 8, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        self.detail_values: dict[str, tk.StringVar] = {key: tk.StringVar(value="—") for key in ("Type", "Scope", "Destination")}
        for row, key in enumerate(self.detail_values, 1):
            tk.Label(card, text=key, bg=self.card, fg=self.muted, font=("TkDefaultFont", 9)).grid(row=row, column=0, sticky="w", pady=(10 if row == 1 else 5, 0))
            tk.Label(card, textvariable=self.detail_values[key], bg=self.card, fg=self.text, font=("TkDefaultFont", 9), wraplength=330, justify="right").grid(row=row, column=1, sticky="e", pady=(10 if row == 1 else 5, 0))
        self.install_button = ttk.Button(card, text="Install application", style="Accent.TButton", command=self.install)
        self.install_button.state(["disabled"])
        self.install_button.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        return card

    def _status_card(self, parent: tk.Misc) -> tk.Frame:
        card = self._card(parent)
        card.columnconfigure(0, weight=1)
        self.status_indicator = tk.Label(card, text="●", bg=self.card, fg=self.muted, font=("TkDefaultFont", 12))
        self.status_indicator.grid(row=0, column=0, sticky="w")
        tk.Label(card, text="INSTALL STATUS", bg=self.card, fg="#b9c3d9", font=("TkDefaultFont", 8, "bold")).grid(row=0, column=0, sticky="w", padx=(20, 0))
        tk.Label(card, textvariable=self.status, bg=self.card, fg=self.text, font=("TkDefaultFont", 10), wraplength=440, justify="left").grid(row=1, column=0, sticky="w", pady=(8, 8))
        self.progress = ttk.Progressbar(card, mode="indeterminate", style="App.Horizontal.TProgressbar")
        self.progress.grid(row=2, column=0, sticky="ew")
        return card

    def _installed_card(self, parent: tk.Misc) -> tk.Frame:
        card = self._card(parent)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)
        heading = tk.Frame(card, bg=self.card)
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        heading.columnconfigure(0, weight=1)
        tk.Label(heading, text="Installed applications", bg=self.card, fg=self.text, font=("TkDefaultFont", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Button(heading, text="↻", style="Quiet.TButton", command=self.refresh_installations).grid(row=0, column=1, sticky="e")
        self.installed_list = tk.Frame(card, bg=self.card)
        self.installed_list.grid(row=1, column=0, sticky="nsew")
        return card

    def _developer_card(self, parent: tk.Misc) -> tk.Frame:
        card = tk.Frame(parent, bg=self.background, padx=2, pady=2)
        tk.Label(card, text="Built by Mohammad Larki", bg=self.background, fg="#707d95", font=("TkDefaultFont", 8)).grid(row=0, column=0, sticky="w")
        for column, (label, url) in enumerate(DEVELOPER_LINKS.items(), 1):
            link = tk.Label(card, text=label, bg=self.background, fg="#9380ee", cursor="hand2", font=("TkDefaultFont", 8, "underline"))
            link.grid(row=0, column=column, padx=(12, 0))
            link.bind("<Button-1>", lambda _event, target=url: webbrowser.open(target))
        return card

    def _enable_optional_drop_target(self) -> None:
        """Use TkDND when available; clicking the zone remains the universal fallback."""
        try:
            from tkinterdnd2 import DND_FILES  # type: ignore[import-not-found]
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._handle_drop)
            self.package_meta.set("Drop a package here or click to browse")
        except (ImportError, AttributeError):
            self.package_meta.set("Click to browse · optional drag-and-drop needs TkDND")

    def _handle_drop(self, event: object) -> None:
        value = getattr(event, "data", "")
        paths = self.root.tk.splitlist(value)
        if paths:
            self.select_package(paths[0])

    def choose_package(self) -> None:
        filename = filedialog.askopenfilename(title="Choose application package", filetypes=[("Linux packages", "*.deb *.AppImage *.appimage *.tar.gz *.tgz"), ("All files", "*")])
        if filename:
            self.select_package(filename)

    def select_package(self, filename: str | Path) -> None:
        try:
            details = package_details(filename)
        except ValueError as error:
            self._set_status(str(error), "error")
            messagebox.showerror("Unsupported package", str(error), parent=self.root)
            return
        self.selected_path = Path(filename)
        self.details = details
        self.path_label.set(details.title)
        self.detail_values["Type"].set(details.package_type)
        self.detail_values["Scope"].set(details.scope)
        self.detail_values["Destination"].set(details.destination)
        self.install_button.state(["!disabled"])
        self._set_status(f"{details.package_type} is ready to install.", "ready")

    def install(self) -> None:
        if self.selected_path is None:
            return
        package = detect_package(self.selected_path)
        scope = InstallScope.SYSTEM if package.kind is PackageKind.DEB else InstallScope.USER
        try:
            plan = create_install_plan(self.selected_path, scope=scope)
        except ValueError as error:
            self._set_status(str(error), "error")
            return
        self.install_button.state(["disabled"])
        self.progress.start(10)
        self._set_status("Installing safely…", "working")
        threading.Thread(target=self._install_in_background, args=(plan,), daemon=True).start()

    def _install_in_background(self, plan: InstallationPlan) -> None:
        try:
            result = install_and_record(plan)
        except Exception as error:
            self.root.after(0, lambda: self._finish_install(str(error), False))
        else:
            location = str(result.executable) if result.executable else "the system package manager"
            self.root.after(0, lambda: self._finish_install(f"Installed successfully · {location}", True))

    def _finish_install(self, message: str, success: bool) -> None:
        self.progress.stop()
        self.install_button.state(["!disabled"])
        self._set_status(message, "success" if success else "error")
        self.refresh_installations()
        if success:
            messagebox.showinfo("AppForge", message, parent=self.root)
        else:
            messagebox.showerror("Installation failed", message, parent=self.root)

    def refresh_installations(self) -> None:
        for child in self.installed_list.winfo_children():
            child.destroy()
        installations = list_installations()
        if not installations:
            tk.Label(self.installed_list, text="No AppForge installations yet.\nYour installed apps will appear here.", bg=self.card, fg=self.muted, justify="left", font=("TkDefaultFont", 10)).pack(anchor="w", pady=18)
            return
        for record in installations:
            self._installation_row(record)

    def _installation_row(self, record: RegisteredInstallation) -> None:
        row = tk.Frame(self.installed_list, bg=self.card_alt, padx=10, pady=10)
        row.pack(fill="x", pady=(0, 8))
        row.columnconfigure(0, weight=1)
        tk.Label(row, text=record.application_id, bg=self.card_alt, fg=self.text, font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(row, text="Installed by AppForge", bg=self.card_alt, fg=self.muted, font=("TkDefaultFont", 8)).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Button(row, text="Launch", style="Quiet.TButton", command=lambda item=record: self.launch_application(item)).grid(row=0, column=1, rowspan=2, padx=(8, 0))
        ttk.Button(row, text="Uninstall", style="Danger.TButton", command=lambda item=record: self.uninstall_application(item)).grid(row=0, column=2, rowspan=2, padx=(6, 0))

    def launch_application(self, record: RegisteredInstallation) -> None:
        if not record.executable:
            self._set_status("This system package is launched by your package manager.", "error")
            return
        executable = Path(record.executable).resolve()
        install_directory = Path(record.install_directory).resolve()
        if install_directory not in executable.parents or not executable.is_file():
            self._set_status("The installed executable is unavailable or unsafe to launch.", "error")
            return
        command = [str(executable)]
        if (executable.parent / "chrome-sandbox").is_file() and (executable.parent / "resources" / "app.asar").is_file():
            command.append("--no-sandbox")
        try:
            subprocess.Popen(command, cwd=executable.parent, start_new_session=True)
        except OSError as error:
            self._set_status(f"Could not launch {record.application_id}: {error}", "error")
            return
        self._set_status(f"Launched {record.application_id}.", "success")

    def uninstall_application(self, record: RegisteredInstallation) -> None:
        if not messagebox.askyesno("Confirm uninstall", f"Remove {record.application_id}, its files, and its launcher?", parent=self.root):
            return
        try:
            uninstall(record.application_id)
        except ValueError as error:
            self._set_status(str(error), "error")
            messagebox.showerror("Cannot uninstall", str(error), parent=self.root)
            return
        self._set_status(f"Uninstalled {record.application_id}. It has been removed from Applications.", "success")
        self.refresh_installations()

    def _set_status(self, message: str, tone: str) -> None:
        colors = {"idle": self.muted, "ready": "#bfaeff", "working": "#8db6ff", "success": self.success, "error": self.danger}
        self.status.set(message)
        self.status_tone.set(tone)
        self.status_indicator.configure(fg=colors.get(tone, self.muted))


def main() -> int:
    """Create the application window when a graphical desktop is available."""
    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(f"AppForge could not open a desktop window: {error}", file=sys.stderr)
        print("Run AppForge from a graphical desktop session with a display available.", file=sys.stderr)
        return 1
    AppForgeWindow(root)
    root.mainloop()
    return 0
