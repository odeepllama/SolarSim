#!/usr/bin/env python3
"""
Quick Start Script for RP2040:bit Deployment

This script provides an interactive menu for building and flashing your code.
Perfect for users who want a simple interface without remembering commands.

Usage:
    python quick_start.py
"""

import os
import sys
import subprocess
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_menu(title, options):
    """Print a menu with options."""
    print_header(title)
    for i, option in enumerate(options, 1):
        print(f"  {Colors.OKCYAN}{i}.{Colors.ENDC} {option}")
    print(f"  {Colors.WARNING}0.{Colors.ENDC} Exit")
    print()

def find_python_files():
    """Find all Python files in parent directory."""
    py_files = list(Path('..').glob('*.py'))
    # Exclude script files
    exclude = {'build_uf2.py', 'quick_start.py'}
    py_files = [f for f in py_files if f.name not in exclude]
    return sorted(py_files)

def find_deployment_dirs():
    """Find all deployment directories in parent directory."""
    return sorted([d for d in Path('..').glob('*_deployment') if d.is_dir()])

def build_file(file_path):
    """Build a deployment package for the given file."""
    print_header(f"Building {file_path.name}")
    
    try:
        result = subprocess.run(
            [sys.executable, 'build_uf2.py', str(file_path)],
            check=True
        )
        print(f"\n{Colors.OKGREEN}✓ Build completed successfully!{Colors.ENDC}")
        return True
    except subprocess.CalledProcessError:
        print(f"\n{Colors.FAIL}✗ Build failed{Colors.ENDC}")
        return False
    except FileNotFoundError:
        print(f"\n{Colors.FAIL}✗ build_uf2.py not found{Colors.ENDC}")
        return False

def flash_deployment(deployment_dir, mode='full'):
    """Flash a deployment package."""
    print_header(f"Flashing {deployment_dir.name}")
    
    try:
        args = ['./flash_tool.sh']
        
        if mode == 'code-only':
            args.append('-c')
        elif mode == 'multiple':
            args.append('-m')
        
        args.append(str(deployment_dir))
        
        result = subprocess.run(args, check=True)
        print(f"\n{Colors.OKGREEN}✓ Flashing completed successfully!{Colors.ENDC}")
        return True
    except subprocess.CalledProcessError:
        print(f"\n{Colors.FAIL}✗ Flashing failed{Colors.ENDC}")
        return False
    except FileNotFoundError:
        print(f"\n{Colors.FAIL}✗ flash_tool.sh not found{Colors.ENDC}")
        return False

def build_menu():
    """Show build menu."""
    while True:
        clear_screen()
        py_files = find_python_files()
        
        if not py_files:
            print(f"{Colors.WARNING}No Python files found in current directory{Colors.ENDC}")
            input("\nPress Enter to continue...")
            return
        
        print_menu("Build Deployment Package", [f.name for f in py_files])
        
        try:
            choice = input(f"{Colors.BOLD}Select file to build: {Colors.ENDC}")
            
            if choice == '0':
                return
            
            idx = int(choice) - 1
            if 0 <= idx < len(py_files):
                if build_file(py_files[idx]):
                    input("\nPress Enter to continue...")
                else:
                    input("\nPress Enter to continue...")
            else:
                print(f"{Colors.FAIL}Invalid choice{Colors.ENDC}")
                input("\nPress Enter to continue...")
        except (ValueError, IndexError):
            print(f"{Colors.FAIL}Invalid choice{Colors.ENDC}")
            input("\nPress Enter to continue...")

def flash_menu():
    """Show flash menu."""
    while True:
        clear_screen()
        deployments = find_deployment_dirs()
        
        if not deployments:
            print(f"{Colors.WARNING}No deployment packages found{Colors.ENDC}")
            print(f"\n{Colors.OKCYAN}Tip: Build a package first from the main menu{Colors.ENDC}")
            input("\nPress Enter to continue...")
            return
        
        print_menu("Flash Device", [d.name for d in deployments])
        
        try:
            choice = input(f"{Colors.BOLD}Select deployment package: {Colors.ENDC}")
            
            if choice == '0':
                return
            
            idx = int(choice) - 1
            if 0 <= idx < len(deployments):
                # Sub-menu for flash options
                clear_screen()
                print_menu(f"Flash Options - {deployments[idx].name}", [
                    "Flash single device (firmware + code)",
                    "Flash multiple devices",
                    "Update code only (faster)"
                ])
                
                flash_choice = input(f"{Colors.BOLD}Select flash mode: {Colors.ENDC}")
                
                if flash_choice == '0':
                    continue
                elif flash_choice == '1':
                    flash_deployment(deployments[idx], 'full')
                elif flash_choice == '2':
                    flash_deployment(deployments[idx], 'multiple')
                elif flash_choice == '3':
                    flash_deployment(deployments[idx], 'code-only')
                else:
                    print(f"{Colors.FAIL}Invalid choice{Colors.ENDC}")
                
                input("\nPress Enter to continue...")
            else:
                print(f"{Colors.FAIL}Invalid choice{Colors.ENDC}")
                input("\nPress Enter to continue...")
        except (ValueError, IndexError):
            print(f"{Colors.FAIL}Invalid choice{Colors.ENDC}")
            input("\nPress Enter to continue...")

def quick_workflow():
    """Quick workflow: build current SolarSimulator.py and flash."""
    clear_screen()
    print_header("Quick Build & Flash Workflow")
    
    solar_sim = Path('SolarSimulator.py')
    
    if not solar_sim.exists():
        print(f"{Colors.FAIL}✗ SolarSimulator.py not found{Colors.ENDC}")
        input("\nPress Enter to continue...")
        return
    
    print(f"{Colors.OKCYAN}This will:{Colors.ENDC}")
    print("  1. Build a deployment package from SolarSimulator.py")
    print("  2. Flash it to your RP2040:bit device")
    print()
    
    confirm = input(f"{Colors.BOLD}Continue? (y/n): {Colors.ENDC}")
    
    if confirm.lower() != 'y':
        return
    
    # Build
    if not build_file(solar_sim):
        input("\nPress Enter to continue...")
        return
    
    # Flash
    deployment = Path('SolarSimulator_deployment')
    if deployment.exists():
        print()
        flash_deployment(deployment, 'full')
    else:
        print(f"{Colors.FAIL}✗ Deployment directory not created{Colors.ENDC}")
    
    input("\nPress Enter to continue...")

def show_help():
    """Show help information."""
    clear_screen()
    print_header("Help & Instructions")
    
    print(f"{Colors.BOLD}Quick Start:{Colors.ENDC}")
    print("  1. Build a deployment package from the main menu")
    print("  2. Connect your RP2040:bit device")
    print("  3. Flash the package to your device")
    print()
    
    print(f"{Colors.BOLD}Building:{Colors.ENDC}")
    print("  - Select 'Build' from main menu")
    print("  - Choose your Python file")
    print("  - A deployment folder will be created")
    print()
    
    print(f"{Colors.BOLD}Flashing:{Colors.ENDC}")
    print("  - Select 'Flash' from main menu")
    print("  - Choose your deployment package")
    print("  - Follow on-screen instructions")
    print()
    
    print(f"{Colors.BOLD}Hardware Setup:{Colors.ENDC}")
    print("  - Hold BOOTSEL button on RP2040:bit")
    print("  - Connect USB cable (while holding BOOTSEL)")
    print("  - Release BOOTSEL")
    print("  - Device appears as RPI-RP2 drive")
    print()
    
    print(f"{Colors.BOLD}Updating Code:{Colors.ENDC}")
    print("  - Use 'Update code only' flash option")
    print("  - Much faster than full flash")
    print("  - Only re-uploads your Python code")
    print()
    
    print(f"{Colors.BOLD}Multiple Devices:{Colors.ENDC}")
    print("  - Use 'Flash multiple devices' option")
    print("  - Flash first device")
    print("  - Disconnect and connect next device")
    print("  - Repeat")
    print()
    
    print(f"{Colors.BOLD}Files Created:{Colors.ENDC}")
    print("  - [name]_deployment/    - Deployment package folder")
    print("    ├── 1_flash_firmware.uf2  - MicroPython firmware")
    print("    ├── 2_upload_code.py      - Your Python code")
    print("    └── README.txt            - Detailed instructions")
    print()
    
    print(f"{Colors.BOLD}Documentation:{Colors.ENDC}")
    print("  - See BUILD_INSTRUCTIONS.md for detailed guide")
    print("  - Check README.txt in deployment folders")
    print()
    
    input("Press Enter to continue...")

def main_menu():
    """Show main menu."""
    while True:
        clear_screen()
        print_menu("RP2040:bit Quick Start Tool", [
            "Build deployment package",
            "Flash to device",
            "Quick workflow (build & flash SolarSimulator.py)",
            "View help & instructions"
        ])
        
        choice = input(f"{Colors.BOLD}Select option: {Colors.ENDC}")
        
        if choice == '0':
            print(f"\n{Colors.OKGREEN}Goodbye!{Colors.ENDC}\n")
            sys.exit(0)
        elif choice == '1':
            build_menu()
        elif choice == '2':
            flash_menu()
        elif choice == '3':
            quick_workflow()
        elif choice == '4':
            show_help()
        else:
            print(f"{Colors.FAIL}Invalid choice{Colors.ENDC}")
            input("\nPress Enter to continue...")

def check_dependencies():
    """Check if required files exist."""
    required_files = ['build_uf2.py', 'flash_tool.sh']
    missing = [f for f in required_files if not Path(f).exists()]
    
    if missing:
        print(f"{Colors.FAIL}✗ Missing required files: {', '.join(missing)}{Colors.ENDC}")
        print(f"\n{Colors.WARNING}Make sure you're running this from the build_tools directory{Colors.ENDC}")
        sys.exit(1)
    
    # Check if flash_tool.sh is executable
    flash_tool = Path('flash_tool.sh')
    if not os.access(flash_tool, os.X_OK):
        print(f"{Colors.WARNING}⚠ flash_tool.sh is not executable{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Attempting to fix...{Colors.ENDC}")
        try:
            os.chmod(flash_tool, 0o755)
            print(f"{Colors.OKGREEN}✓ Fixed{Colors.ENDC}\n")
        except Exception as e:
            print(f"{Colors.FAIL}✗ Failed to fix: {e}{Colors.ENDC}")
            print(f"{Colors.OKCYAN}Run: chmod +x flash_tool.sh{Colors.ENDC}\n")

def main():
    """Main entry point."""
    check_dependencies()
    
    # Check if running from correct directory
    if not Path('../SolarSimulator.py').exists() and not list(Path('..').glob('*.py')):
        print(f"{Colors.WARNING}⚠ No Python files found in parent directory{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Make sure you're in the build_tools directory{Colors.ENDC}\n")
        sys.exit(1)
    
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.OKGREEN}Goodbye!{Colors.ENDC}\n")
        sys.exit(0)

if __name__ == '__main__':
    main()
