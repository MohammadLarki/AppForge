"""Tkinter implementation of the AppForge desktop interface."""

from __future__ import annotations

from pathlib import Path
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .detector import PackageKind, detect_package
from .installer import InstallScope, InstallationPlan, create_install_plan
from .registry import install_and_record, list_installations, uninstall


class AppForgeWindow(ttk.Frame):
    """A small, single-purpose application installer window."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, padding=20)
        self.root = root
        self.selected_path: Path | None = None
        self.pack(fill=tk.BOTH, expand=True)
        root.title("AppForge")
        root.minsize(540, 240)

        self.status = tk.StringVar(value="Choose a package to begin.")
        self.path_label = tk.StringVar(value="No package selected")
        self.install_button = ttk.Button(self, text="Install", command=self.install)
        self.install_button.state(["disabled"])
        self.uninstall_button = ttk.Button(self, text="Uninstall…", command=self.uninstall_application)

        ttk.Label(self, text="Install a Linux application", font=("TkDefaultFont", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(self, textvariable=self.path_label, wraplength=500).pack(anchor=tk.W, pady=(18, 8))
        ttk.Button(self, text="Choose package…", command=self.choose_package).pack(anchor=tk.W)
        self.install_button.pack(anchor=tk.W, pady=(12, 16))
        self.uninstall_button.pack(anchor=tk.W, pady=(0, 16))
        ttk.Separator(self).pack(fill=tk.X)
        ttk.Label(self, textvariable=self.status, wraplength=500).pack(anchor=tk.W, pady=(14, 0))

    def choose_package(self) -> None:
        filename = filedialog.askopenfilename(
            title="Choose application package",
            filetypes=[("Linux packages", "*.deb *.AppImage *.appimage *.tar.gz *.tgz"), ("All files", "*")],
        )
        if not filename:
            return
        package = detect_package(filename)
        if not package.supported:
            messagebox.showerror("Unsupported package", "Choose a supported Linux package.")
            return
        self.selected_path = Path(filename)
        self.path_label.set(str(self.selected_path))
        details = package.kind.value
        if package.kind is PackageKind.DEB:
            details += " — administrator permission will be requested"
        self.status.set(f"Ready to install: {details}")
        self.install_button.state(["!disabled"])

    def install(self) -> None:
        if self.selected_path is None:
            return
        package = detect_package(self.selected_path)
        scope = InstallScope.SYSTEM if package.kind is PackageKind.DEB else InstallScope.USER
        try:
            plan = create_install_plan(self.selected_path, scope=scope)
        except ValueError as error:
            messagebox.showerror("Cannot install", str(error))
            return
        self.install_button.state(["disabled"])
        self.status.set("Installing…")
        threading.Thread(target=self._install_in_background, args=(plan,), daemon=True).start()

    def _install_in_background(self, plan: InstallationPlan) -> None:
        try:
            result = install_and_record(plan)
        except Exception as error:
            self.root.after(0, lambda: self._finish_install(str(error), False))
        else:
            location = str(result.executable) if result.executable else "the system package manager"
            self.root.after(0, lambda: self._finish_install(f"Installed successfully: {location}", True))

    def _finish_install(self, message: str, success: bool) -> None:
        self.status.set(message)
        self.install_button.state(["!disabled"])
        if success:
            messagebox.showinfo("AppForge", message)
        else:
            messagebox.showerror("Installation failed", message)

    def uninstall_application(self) -> None:
        """Safely remove one user-scope application recorded by AppForge."""
        installations = list_installations()
        if not installations:
            messagebox.showinfo("AppForge", "No user applications installed by AppForge were found.")
            return
        choices = ", ".join(item.application_id for item in installations)
        application_id = simpledialog.askstring(
            "Uninstall application",
            f"Enter the application ID to remove:\n{choices}",
            parent=self.root,
        )
        if not application_id:
            return
        if application_id not in {item.application_id for item in installations}:
            messagebox.showerror("Cannot uninstall", "Choose an application installed by AppForge.")
            return
        if not messagebox.askyesno("Confirm uninstall", f"Remove {application_id} and its launcher?", parent=self.root):
            return
        try:
            uninstall(application_id)
        except ValueError as error:
            messagebox.showerror("Cannot uninstall", str(error))
            return
        self.status.set(f"Uninstalled: {application_id}")
        messagebox.showinfo("AppForge", f"Removed {application_id} from Applications.")


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
