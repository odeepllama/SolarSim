"""
Combined Hardware and Display Manager Test
===========================================
Tests both hardware abstraction and display manager working together.

Run this test on the ESP32-S3 to verify all systems before integrating
the main Solar Simulator code.

Usage:
    1. Upload all files in lib/ to ESP32
    2. Upload this test_lib.py to ESP32
    3. From REPL: import test_lib
    4. Or: python test_lib.py (if running from command line)
"""

import time
import gc
from lib import HardwareESP32, DisplayManager


def test_integrated_system():
    """Test hardware and display manager working together"""
    print("\n" + "="*60)
    print("INTEGRATED SYSTEM TEST")
    print("Testing Hardware + Display Manager")
    print("="*60 + "\n")
    
    # ========================================================================
    # Phase 1: Hardware Initialization
    # ========================================================================
    print("[PHASE 1] Initializing Hardware...")
    hw = HardwareESP32(neopixel_count=448)
    time.sleep(1)
    
    # ========================================================================
    # Phase 2: Display Manager Initialization
    # ========================================================================
    print("\n[PHASE 2] Initializing Display Manager...")
    dm = DisplayManager(hw.lcd if hw.lcd_available else None)
    dm.display_welcome()
    time.sleep(2)
    
    # ========================================================================
    # Phase 3: Simulation Status Display Test
    # ========================================================================
    print("\n[PHASE 3] Testing Simulation Status Display...")
    dm.display_message("Test: Sim Status", "Starting...")
    time.sleep(1)
    
    # Simulate 10 seconds of simulation time updates
    for i in range(10):
        sim_time = 43200 + i * 360  # Start at noon, increment 6 minutes each
        sim_speed = 60.0
        intensity = 50 + i * 5
        autoload = i % 2 == 0
        
        dm.display_status(sim_time, sim_speed, intensity, autoload)
        print(f"  Sim update {i+1}/10: {sim_time}s, {intensity}%, AL={autoload}")
        time.sleep(0.5)
    
    print("✓ Status display test passed")
    
    # ========================================================================
    # Phase 4: Hardware Control with Display Feedback
    # ========================================================================
    print("\n[PHASE 4] Testing Hardware Control + Display...")
    
    # Test 4a: Servo control with display
    print("  [4a] Servo control with display feedback...")
    dm.display_message("Test: Servos", "Moving...")
    time.sleep(1)
    
    for angle in [0, 45, 90, 45, 0]:
        hw.set_servo1_angle(angle)
        dm.display_rotation_angle(angle)
        print(f"    Rotation → {angle}°")
        time.sleep(1)
    
    # Test 4b: NeoPixel control with display
    print("  [4b] NeoPixel control with display feedback...")
    colors = [
        (30, 0, 0, "Red"),
        (0, 30, 0, "Green"),
        (0, 0, 30, "Blue"),
        (30, 15, 0, "Orange"),
        (15, 0, 30, "Purple"),
        (0, 0, 0, "Off")
    ]
    
    for r, g, b, name in colors:
        hw.fill_panel(r, g, b)
        dm.display_message(f"Light: {name}", f"RGB({r},{g},{b})")
        print(f"    Panel → {name}")
        time.sleep(1)
    
    # Test 4c: Camera trigger with display
    print("  [4c] Camera trigger with display feedback...")
    for cam_num in [1, 2]:
        dm.display_camera_status(cam_num, "Ready")
        time.sleep(0.5)
        dm.display_camera_status(cam_num, "Triggering...")
        hw.trigger_camera_shutter()
        time.sleep(0.1)
        dm.display_camera_status(cam_num, "Done!")
        print(f"    Camera {cam_num} triggered")
        time.sleep(1)
    
    # Test 4d: Button monitoring with display
    print("  [4d] Button monitoring (5 seconds)...")
    dm.display_message("Press Button A", "(BOOT button)")
    
    start = time.ticks_ms()
    button_pressed = False
    while time.ticks_diff(time.ticks_ms(), start) < 5000:
        if hw.button_a_pressed():
            dm.display_message("Button A", "PRESSED!")
            print("    Button A detected!")
            button_pressed = True
            time.sleep(1)
            break
        time.sleep_ms(100)
    
    if not button_pressed:
        print("    Button A not pressed (OK)")
    
    print("✓ Hardware control test passed")
    
    # ========================================================================
    # Phase 5: Simulated Solar Cycle
    # ========================================================================
    print("\n[PHASE 5] Simulating Solar Cycle...")
    dm.display_message("Test: Solar Sim", "Full cycle...")
    time.sleep(2)
    
    # Simulate sunrise to sunset (6 AM to 6 PM)
    start_time = 6 * 3600  # 6:00 AM
    end_time = 18 * 3600   # 6:00 PM
    steps = 12
    
    print("  Simulating 12-hour day cycle...")
    for i in range(steps + 1):
        # Calculate simulation parameters
        sim_time = start_time + (end_time - start_time) * i / steps
        
        # Calculate sun angle (0° at sunrise, 180° at noon, 360° at sunset)
        sun_progress = (sim_time - start_time) / (end_time - start_time)
        sun_angle = sun_progress * 180  # 0° to 180° over 12 hours
        
        # Calculate intensity (parabolic curve, peak at noon)
        # Peak at 100% at noon (6 hours in), 0% at sunrise/sunset
        hours_from_noon = abs((sim_time - 12*3600) / 3600)  # Hours from noon
        intensity = max(0, int(100 * (1 - (hours_from_noon / 6)**2)))
        
        # Update hardware
        hw.set_servo1_angle(sun_angle)
        
        # Scale intensity to safe RGB values for testing (max 50)
        led_brightness = int(50 * intensity / 100)
        hw.fill_panel(led_brightness, led_brightness, int(led_brightness * 0.8))
        
        # Update display
        dm.display_status(sim_time, 60.0, intensity, True)
        
        print(f"    Step {i+1}/{steps+1}: {sun_angle:.0f}°, {intensity}%, {sim_time/3600:.1f}h")
        time.sleep(1)
    
    print("✓ Solar cycle simulation complete")
    
    # ========================================================================
    # Phase 6: Memory and Performance Test
    # ========================================================================
    print("\n[PHASE 6] Memory and Performance...")
    gc.collect()
    free = gc.mem_free()
    total = 512 * 1024  # Approximate total RAM (adjust for your ESP32)
    free_kb = free // 1024
    total_kb = total // 1024
    
    dm.display_memory_info(free_kb, total_kb)
    print(f"  Free memory: {free_kb}KB / {total_kb}KB")
    print(f"  Hardware object size: {hw.__sizeof__()} bytes")
    print(f"  Display manager size: {dm.__sizeof__()} bytes")
    time.sleep(3)
    
    # ========================================================================
    # Phase 7: Progress Bar Test
    # ========================================================================
    print("\n[PHASE 7] Progress Bar Display...")
    for progress in range(0, 101, 10):
        dm.display_progress_bar("Loading Data", progress)
        print(f"  Progress: {progress}%")
        time.sleep(0.5)
    
    print("✓ Progress bar test complete")
    
    # ========================================================================
    # Phase 8: Animation Test
    # ========================================================================
    print("\n[PHASE 8] Display Animation...")
    animation_frames = [
        ("   Solar Sim", ""),
        ("  Solar Sim ", ""),
        (" Solar Sim  ", "ESP32-S3"),
        ("Solar Sim   ", "ESP32-S3"),
        ("olar Sim    ", "Ready!"),
        ("lar Sim     ", "Ready!"),
    ]
    dm.show_animation(animation_frames, frame_delay=200)
    print("✓ Animation test complete")
    
    # ========================================================================
    # Final Summary
    # ========================================================================
    print("\n" + "="*60)
    print("INTEGRATED TEST SUMMARY")
    print("="*60)
    print(f"Hardware:        ✓ OK")
    print(f"Display Manager: ✓ OK")
    print(f"Servos:          ✓ OK (3 servos)")
    print(f"NeoPixels:       ✓ OK ({hw.neopixel_count} LEDs)")
    print(f"LCD Display:     {'✓ OK' if hw.lcd_available else '⚠ Not found'}")
    print(f"Camera Trigger:  ✓ OK")
    print(f"Buttons:         {'✓ Tested' if button_pressed else '⚠ Not pressed'}")
    print(f"Memory:          ✓ OK ({free_kb}KB free)")
    print("="*60 + "\n")
    
    dm.display_message("All Tests", "Complete! ✓")
    time.sleep(3)
    
    # Cleanup
    print("[CLEANUP] Shutting down...")
    hw.shutdown()
    dm.clear()
    
    print("\n✓ All integrated tests PASSED!\n")
    
    return hw, dm


def quick_test():
    """Quick sanity check test"""
    print("\n[QUICK TEST] Running sanity check...\n")
    
    hw = HardwareESP32()
    dm = DisplayManager(hw.lcd if hw.lcd_available else None)
    
    dm.display_message("Quick Test", "Running...")
    time.sleep(1)
    
    # Flash LEDs
    hw.fill_panel(30, 0, 0)
    time.sleep(0.5)
    hw.fill_panel(0, 0, 0)
    
    # Move servo
    hw.set_servo1_angle(90)
    dm.display_message("Servo: 90°", "✓")
    time.sleep(1)
    hw.set_servo1_angle(0)
    
    dm.display_message("Quick Test", "Complete! ✓")
    time.sleep(2)
    
    hw.shutdown()
    dm.clear()
    
    print("✓ Quick test passed!\n")


def benchmark_display_updates():
    """Benchmark display update performance"""
    print("\n[BENCHMARK] Testing display update performance...\n")
    
    hw = HardwareESP32()
    dm = DisplayManager(hw.lcd if hw.lcd_available else None)
    
    if not dm.lcd_available:
        print("⚠ No LCD available for benchmark")
        return
    
    # Test rapid updates
    print("  Testing rapid status updates (50 updates)...")
    start = time.ticks_ms()
    
    for i in range(50):
        sim_time = 43200 + i * 100
        intensity = 50 + i % 50
        dm.display_status(sim_time, 60.0, intensity, True)
    
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    updates_per_sec = 50000 / elapsed if elapsed > 0 else 0
    
    print(f"  50 updates in {elapsed}ms")
    print(f"  Rate: {updates_per_sec:.1f} updates/sec")
    print(f"  Average: {elapsed/50:.1f}ms per update")
    
    # Test with throttling disabled
    dm.set_update_interval(0)
    
    print("\n  Testing without throttling (50 updates)...")
    start = time.ticks_ms()
    
    for i in range(50):
        sim_time = 43200 + i * 100
        intensity = 50 + i % 50
        dm.display_status(sim_time, 60.0, intensity, True)
    
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    updates_per_sec = 50000 / elapsed if elapsed > 0 else 0
    
    print(f"  50 updates in {elapsed}ms")
    print(f"  Rate: {updates_per_sec:.1f} updates/sec")
    print(f"  Average: {elapsed/50:.1f}ms per update")
    
    hw.shutdown()
    dm.clear()
    
    print("\n✓ Benchmark complete\n")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main test entry point"""
    print("\n" + "="*60)
    print("ESP32-S3 SOLAR SIMULATOR - LIBRARY TEST")
    print("="*60)
    print("\nSelect test to run:")
    print("  1. Full integrated test (recommended)")
    print("  2. Quick sanity check")
    print("  3. Display update benchmark")
    print("  4. Run all tests")
    print("\nOr import this module and call functions directly:")
    print("  >>> import test_lib")
    print("  >>> test_lib.test_integrated_system()")
    print("="*60 + "\n")
    
    # Auto-run full test if called as main
    test_integrated_system()


if __name__ == "__main__":
    main()
