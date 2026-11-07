# SPDX-License-Identifier: Apache-2.0
"""Device and OS compatibility checker for OptimAI Network CLI.

Detects current operating system, distribution (Arch, Debian, Ubuntu, Fedora,
macOS, Windows), and CPU architecture. Validates compatibility against official
OptimAI Network binaries and retrieves the appropriate download URL.

Design principles:
  - Do NOT force RAM or storage minimums (advisory only; low-spec VPS/devices allowed).
  - Check OS and CPU architecture strictly against upstream distribution builds.
  - Standard library only (zero third-party dependencies).
"""

from __future__ import annotations

import os
import platform
import shutil
import stat
import sys
import urllib.request
from typing import Any, Tuple

# Official OptimAI download endpoints
CLI_URL_LINUX_X86_64 = "https://cli-node.optimai.network/optimai_cli_ubuntu"
CLI_URL_DARWIN_UNIVERSAL = "https://cli-node.optimai.network/optimai_cli_darwin_universal2"
CLI_URL_WINDOWS_X86_64 = "https://cli-node.optimai.network/optimai_cli_windows.exe"


def get_os_info() -> dict[str, str]:
    """Retrieve detailed OS and distribution info for the current machine."""
    system = platform.system()
    machine = platform.machine().lower()
    release = platform.release()

    distro_id = "unknown"
    distro_like = ""
    distro_name = f"{system} {release}"

    if system == "Linux":
        if os.path.isfile("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("ID="):
                            distro_id = line.split("=", 1)[1].strip('"\'').lower()
                        elif line.startswith("ID_LIKE="):
                            distro_like = line.split("=", 1)[1].strip('"\'').lower()
                        elif line.startswith("PRETTY_NAME="):
                            distro_name = line.split("=", 1)[1].strip('"\'')
            except Exception:
                pass
        elif os.path.isfile("/etc/arch-release"):
            distro_id = "arch"
            distro_name = "Arch Linux"
        elif os.path.isfile("/etc/debian_version"):
            distro_id = "debian"
            distro_name = "Debian"
    elif system == "Darwin":
        distro_id = "macos"
        mac_ver = platform.mac_ver()[0] or release
        distro_name = f"macOS {mac_ver}"
    elif system == "Windows":
        distro_id = "windows"
        distro_name = f"Windows {platform.version()}"

    return {
        "system": system,
        "machine": machine,
        "release": release,
        "distro_id": distro_id,
        "distro_like": distro_like,
        "distro_name": distro_name,
    }


def get_system_specs() -> dict[str, Any]:
    """Retrieve system memory and storage advisory metrics without enforcing limits."""
    ram_mb = 0
    disk_free_gb = 0.0

    # RAM
    if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names and "SC_PHYS_PAGES" in os.sysconf_names:
        try:
            ram_mb = int((os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) / (1024 * 1024))
        except (ValueError, OSError):
            pass

    # Disk free space on current volume
    try:
        statvfs = os.statvfs(".")
        disk_free_gb = round((statvfs.f_bavail * statvfs.f_frsize) / (1024 ** 3), 2)
    except (AttributeError, OSError):
        pass

    return {
        "ram_mb": ram_mb,
        "disk_free_gb": disk_free_gb,
    }


def check_device_compatibility(
    os_info: dict[str, str] | None = None,
) -> Tuple[bool, str, dict[str, Any]]:
    """Determine whether the current device/OS can run the OptimAI CLI.

    Returns:
      (is_compatible, message, details)

    Note:
      RAM and storage are NOT enforced. Low-spec environments (1GB VPS, etc.)
      remain compatible as long as OS and architecture are supported.
    """
    info = os_info or get_os_info()
    specs = get_system_specs()

    system = info.get("system", "")
    machine = info.get("machine", "").lower()
    distro_name = info.get("distro_name", "")

    # Normalize architecture aliases
    is_x86_64 = machine in ("x86_64", "amd64", "x64")
    is_arm64 = machine in ("aarch64", "arm64")
    is_32bit = machine in ("i386", "i686", "armv7l", "armv6l", "arm")

    cli_url: str | None = None
    is_compatible = False
    reason = ""

    if system == "Linux":
        if is_x86_64:
            is_compatible = True
            cli_url = CLI_URL_LINUX_X86_64
            reason = f"Compatible: 64-bit Linux ({distro_name}, {machine}). Supported across Arch, Debian, Ubuntu, Fedora, openSUSE, etc."
        elif is_arm64:
            is_compatible = False
            reason = (
                f"Incompatible architecture: Linux {machine} (ARM64). "
                "The upstream OptimAI Network currently only distributes x86_64 ELF binaries for Linux. "
                "ARM64 is supported on macOS (Apple Silicon), but not yet on Linux."
            )
        elif is_32bit:
            is_compatible = False
            reason = f"Incompatible architecture: 32-bit Linux ({machine}). OptimAI CLI requires a 64-bit operating system."
        else:
            is_compatible = False
            reason = f"Incompatible architecture: Unsupported Linux CPU architecture '{machine}'."

    elif system == "Darwin":
        if is_x86_64 or is_arm64:
            is_compatible = True
            cli_url = CLI_URL_DARWIN_UNIVERSAL
            reason = f"Compatible: macOS ({distro_name}, {machine}) supported via universal binary (Intel & Apple Silicon)."
        else:
            is_compatible = False
            reason = f"Incompatible architecture: Unsupported macOS CPU architecture '{machine}'."

    elif system == "Windows":
        if is_x86_64:
            is_compatible = True
            cli_url = CLI_URL_WINDOWS_X86_64
            reason = f"Compatible: 64-bit Windows ({distro_name}, {machine})."
        else:
            is_compatible = False
            reason = f"Incompatible architecture: 32-bit Windows ({machine}). OptimAI CLI requires 64-bit Windows 10/11."

    else:
        is_compatible = False
        reason = f"Incompatible operating system: '{system}'. OptimAI CLI is officially supported on Linux, macOS, and Windows."

    details: dict[str, Any] = {
        **info,
        **specs,
        "is_compatible": is_compatible,
        "reason": reason,
        "cli_url": cli_url,
    }

    return is_compatible, reason, details


def get_compatible_cli_url() -> str | None:
    """Return the official download URL matching the current device, or None if incompatible."""
    is_compat, _msg, details = check_device_compatibility()
    return details.get("cli_url") if is_compat else None


def download_compatible_cli(dest_path: str, url: str | None = None) -> Tuple[bool, str]:
    """Download and install the compatible OptimAI CLI binary to dest_path."""
    target_url = url or get_compatible_cli_url()
    if not target_url:
        _, reason, _ = check_device_compatibility()
        return False, f"Cannot download CLI: Device is not compatible ({reason})"

    dest_dir = os.path.dirname(os.path.abspath(dest_path))
    if not os.access(dest_dir, os.W_OK):
        return False, f"Destination directory '{dest_dir}' is not writable (try with sudo or use a local path like ~/.local/bin/optimai-cli)"

    temp_path = f"{dest_path}.tmp.{os.getpid()}"
    try:
        req = urllib.request.Request(
            target_url,
            headers={"User-Agent": "OptimAI-Node-Controller/1.3.0"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp, open(temp_path, "wb") as out_file:
            shutil.copyfileobj(resp, out_file)

        # Make executable
        st = os.stat(temp_path)
        os.chmod(temp_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        os.replace(temp_path, dest_path)
        return True, f"Successfully installed compatible OptimAI CLI to {dest_path} (from {target_url})"
    except Exception as exc:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return False, f"Download failed: {exc}"
