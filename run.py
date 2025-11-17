#!/usr/bin/env python3
# run.py — unified launcher for Incentiv project
import os
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))

def run_script(script):
    script_path = os.path.join(BASE, script)
    if not os.path.exists(script_path):
        print(f"[!] File not found: {script_path}")
        return
    print(f"[+] Running: {script_path}\n")
    subprocess.run(["python", script_path], cwd=BASE)

def menu():
    while True:
        print("\n=== Incentiv Unified Launcher ===")
        print("1) Run Auto-Register")
        print("2) Run Auto-Register with key mode")
        print("3) Run Incentiv Testnet Bot")
        print("4) Run unified CLI")
        print("5) Exit")
        choice = input("Choose: ").strip()

        if choice == "1":
            run_script("register.py")
        elif choice == "2":
            run_script("register_mode.py")
        elif choice == "3":
            run_script("bot.py")
        elif choice == "4":
            run_script("main.py")
        elif choice == "5":
            print("Bye.")
            break
        else:
            print("Invalid choice. Please select 1–5.")

if __name__ == "__main__":
    menu()
