esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash  --flash_size 16MB -z 0x1000 ./lv_micropython_1.14_168aa6a_esp32_idf4.0_m5stack_m5core2.bin

