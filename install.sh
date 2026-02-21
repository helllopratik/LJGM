sudo apt install python3-evdev python3-uinput
sudo modprobe uinput
echo uinput | sudo tee -a /etc/modules
sudo apt install python3-pyqt6