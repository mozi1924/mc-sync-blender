#!/usr/bin/env python3
"""
Yefira Mod Cross-Version Verification & Test Automation Suite
Checks static invariants, runs core integration tests, validates multi-version builds,
and inspects compiled artifacts.
"""

import sys
import os
import re
import json
import zipfile
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Color terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def log_info(msg):
    print(f"{CYAN}[INFO]{RESET} {msg}")

def log_success(msg):
    print(f"{GREEN}[PASS]{RESET} {msg}")

def log_warn(msg):
    print(f"{YELLOW}[WARN]{RESET} {msg}")

def log_error(msg):
    print(f"{RED}[FAIL]{RESET} {msg}")

def step(title):
    print(f"\n{BOLD}==================================================")
    print(f"  {title}")
    print(f"=================================================={RESET}")

def test_language_files():
    step("1. Checking Translation Files for Illegal Specifiers (%d)")
    lang_dir = ROOT_DIR / "common-core/src/main/resources/assets/yefira/lang"
    passed = True

    # Minecraft TranslatableContents FORMAT_PATTERN: %(?:(\d+)\$)?([A-Za-z%]|$)
    # Group 2 must be 's' or '%'
    mc_format_pattern = re.compile(r"%(?:(\d+)\$)?([A-Za-z%]|$)")

    for lang_file in lang_dir.glob("*.json"):
        with open(lang_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                log_error(f"Failed to parse JSON {lang_file.name}: {e}")
                passed = False
                continue

            for key, val in data.items():
                for match in mc_format_pattern.finditer(val):
                    spec = match.group(2)
                    if spec not in ("s", "%"):
                        log_error(f"{lang_file.name} [{key}]: Illegal format specifier '%{spec}' in '{val}'. Only '%s' is allowed.")
                        passed = False

    if passed:
        log_success("All language files use valid Minecraft '%s' placeholders!")
    return passed

def test_mixin_signatures():
    step("2. Validating Mixin Invariants Across Minecraft Versions")
    passed = True
    versions = ["1.20.1", "1.20.4", "1.21.1", "1.21.4", "26.2"]

    for ver in versions:
        mouse_mixin = ROOT_DIR / f"versions/{ver}/common/src/main/java/com/mozi1924/yefira/client/mixin/MouseHandlerMixin.java"
        if not mouse_mixin.exists():
            log_error(f"Missing MouseHandlerMixin in {ver}")
            passed = False
            continue

        content = mouse_mixin.read_text(encoding="utf-8")

        # 1.20.1 and 1.20.4 MUST have onTurnPlayer(CallbackInfo ci) without double
        if ver in ["1.20.1", "1.20.4"]:
            if "onTurnPlayer(double" in content:
                log_error(f"{ver} MouseHandlerMixin has illegal 'double delta' parameter for turnPlayer!")
                passed = False
            elif "onTurnPlayer(CallbackInfo ci)" in content:
                log_success(f"{ver} MouseHandlerMixin correctly uses zero-argument turnPlayer signature")
            else:
                log_error(f"{ver} MouseHandlerMixin missing expected onTurnPlayer method")
                passed = False
        else:
            # 1.21+ has turnPlayer(double delta)
            if "onTurnPlayer(double" in content:
                log_success(f"{ver} MouseHandlerMixin correctly uses (double delta) turnPlayer signature")
            else:
                log_error(f"{ver} MouseHandlerMixin missing expected (double delta) parameter for 1.21+!")
                passed = False

        # Verify require = 0 on turnPlayer
        if "@Inject(method = \"turnPlayer\", at = @At(\"HEAD\"), cancellable = true, require = 0)" not in content:
            log_warn(f"{ver} MouseHandlerMixin recommended to have require = 0 for turnPlayer injection safety")

    return passed

def test_permission_null_guards():
    step("3. Validating SelectionCommand & Screen Permission Null Guards")
    passed = True
    versions = ["1.20.1", "1.20.4", "1.21.1", "1.21.4", "26.2"]

    for ver in versions:
        cmd_file = ROOT_DIR / f"versions/{ver}/common/src/main/java/com/mozi1924/yefira/command/SelectionCommand.java"
        if not cmd_file.exists():
            log_error(f"Missing SelectionCommand in {ver}")
            passed = False
            continue
        content = cmd_file.read_text(encoding="utf-8")
        if "source.getServer() != null" not in content:
            log_error(f"{ver} SelectionCommand.hasAdminPermission is missing 'source.getServer() != null' null check!")
            passed = False
        else:
            log_success(f"{ver} SelectionCommand has safe null check on source.getServer()")

        screen_file = ROOT_DIR / f"versions/{ver}/common/src/main/java/com/mozi1924/yefira/client/gui/YefiraScreen.java"
        if screen_file.exists():
            screen_content = screen_file.read_text(encoding="utf-8")
            if "SelectionBox sel = mgr.getCurrentSelection();" in screen_content and "if (sel != null" in screen_content:
                log_success(f"{ver} YefiraScreen has thread-safe SelectionBox null guard")
            else:
                log_error(f"{ver} YefiraScreen missing race-condition check for getCurrentSelection()")
                passed = False

    return passed

def test_core_gradle_tests():
    step("4. Running JUnit Core Unit & Integration Tests")
    cmd = ["./gradlew", "test"]
    env = os.environ.copy()
    env["JAVA_HOME"] = "/usr/lib/jvm/java-17-temurin-jdk"
    
    res = subprocess.run(cmd, cwd=str(ROOT_DIR / "versions/1.20.1"), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if res.returncode == 0:
        log_success("All JUnit unit & integration tests passed successfully!")
        return True
    else:
        log_error(f"JUnit tests failed:\n{res.stdout}")
        return False

def test_build_all_artifacts():
    step("5. Building and Verifying Mod Artifacts Across All Versions")
    build_cmd = ["./gradlew", "buildAll"]
    res = subprocess.run(build_cmd, cwd=str(ROOT_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if res.returncode != 0:
        log_error(f"buildAll failed:\n{res.stdout}")
        return False

    expected_jars = [
        "yefira-fabric-mc1.20-1.20.1-1.0.0.jar",
        "yefira-forge-mc1.20-1.20.1-1.0.0.jar",
        "yefira-fabric-mc1.20.2-1.20.4-1.0.0.jar",
        "yefira-neoforge-mc1.20.2-1.20.4-1.0.0.jar",
        "yefira-fabric-mc1.20.5-1.21.1-1.0.0.jar",
        "yefira-neoforge-mc1.20.5-1.21.1-1.0.0.jar",
        "yefira-fabric-mc1.21.2-1.21.4-1.0.0.jar",
        "yefira-neoforge-mc1.21.2-1.21.4-1.0.0.jar",
        "yefira-fabric-mc26.2-1.0.0.jar",
        "yefira-neoforge-mc26.2-1.0.0.jar"
    ]

    dist_dir = ROOT_DIR / "build/dist"
    all_present = True
    for jar_name in expected_jars:
        jar_path = dist_dir / jar_name
        if not jar_path.exists():
            log_error(f"Missing expected jar: {jar_name}")
            all_present = False
            continue

        size = jar_path.stat().st_size
        if size < 10000:
            log_error(f"Jar {jar_name} seems too small ({size} bytes)")
            all_present = False
            continue

        # Inspect jar contents
        with zipfile.ZipFile(jar_path, 'r') as zf:
            namelist = zf.namelist()
            # Ensure YefiraScreen and MouseHandlerMixin are included
            if not any("MouseHandlerMixin" in n for n in namelist):
                log_error(f"{jar_name} missing MouseHandlerMixin class!")
                all_present = False
            if not any("YefiraScreen" in n for n in namelist):
                log_error(f"{jar_name} missing YefiraScreen class!")
                all_present = False

        log_success(f"Verified {jar_name} ({size // 1024} KB)")

    return all_present

def main():
    print(f"\n{BOLD}{CYAN}=== Starting Yefira Mod Multi-Version Verification Suite ==={RESET}\n")
    results = []

    results.append(("Language File Check", test_language_files()))
    results.append(("Mixin Invariant Check", test_mixin_signatures()))
    results.append(("Permission & Race Condition Check", test_permission_null_guards()))
    results.append(("JUnit Integration Tests", test_core_gradle_tests()))
    results.append(("Multi-Version Artifact Build", test_build_all_artifacts()))

    step("VERIFICATION SUMMARY")
    all_ok = True
    for name, ok in results:
        status = f"{GREEN}PASSED{RESET}" if ok else f"{RED}FAILED{RESET}"
        print(f" - {name:<35}: {status}")
        if not ok:
            all_ok = False

    if all_ok:
        print(f"\n{BOLD}{GREEN}>>> ALL CHECKS AND VERIFICATIONS PASSED SUCCESSFULLY! <<<{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{BOLD}{RED}>>> SOME CHECKS FAILED. Please review the errors above. <<<{RESET}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
