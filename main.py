import sys
from core.device_detector import DeviceDetector
from core.virtual_gamepad import VirtualGamepad
from core.processor import InputProcessor


TARGET_VID = "0079"
TARGET_PID = "0006"
TARGET_NAME = "Joystick"


def main():

    detector = DeviceDetector(
        vid=TARGET_VID,
        pid=TARGET_PID,
        name=TARGET_NAME
    )

    device = detector.find()

    if not device:
        print("No compatible device found.")
        sys.exit(1)

    print(f"[+] Found: {device.path}")

    virtual = VirtualGamepad()
    print("[+] Virtual Gamepad Created")

    processor = InputProcessor(device, virtual)

    try:
        processor.start()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        device.ungrab()


if __name__ == "__main__":
    main()