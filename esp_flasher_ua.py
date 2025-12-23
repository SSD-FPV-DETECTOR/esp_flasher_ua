import sys
import argparse
import signal
import logging
import threading
import time
import esptool

#From flash_download_tool v3.9.9
port_speeds = [19200, 115200, 230400, 460800, 576000, 921600, 1152000]
port_speed_default = 921600

#From esptool v5.1.0
chip_names = ["auto", "esp8266", "esp32", "esp32s2", "esp32s3", "esp32c3", "esp32c2", "esp32c6", "esp32c61", "esp32c5", "esp32h2", "esp32h21", "esp32p4", "esp32h4"]
flash_frequencies = ["keep", "80m", "60m", "48m", "40m", "30m", "26m", "24m", "20m", "16m", "15m", "12m"]
flash_modes = ["keep", "qio", "qout", "dio", "dout"]
flash_sizes = ["detect", "keep", "256KB", "512KB", "1MB", "2MB", "2MB-c1", "4MB", "4MB-c1", "8MB", "16MB", "32MB", "64MB", "128MB"]
firmware_bin_path_default = "firmware.bin"
bootloader_bin_path_default = "flash_bins/bootloader/bootloader_esp32_dio_40m.bin"
partitions_bin_path_default = "flash_bins/partitions/default.bin"
bootselect_bin_path_default = "flash_bins/bootselect/boot_app0.bin"


app_name = "ESP Flasher UA"
app_banner_text = "Слава Україні!"


def run_esptool_noexcept(args_str: str) -> bool:
    try:
        esptool.main([args_str])
    except Exception as e:
        logging.error(str(e))
        return False
    return True
            


def main() -> int:
    
    guiMode = ('--gui' in sys.argv)
    if(guiMode):
        import six
        from gooey import Gooey, GooeyParser
        parser = GooeyParser(description = app_banner_text)
    else:
        parser = argparse.ArgumentParser(description = app_banner_text)
        
    actionsGroup = parser.add_argument_group("Дії")
    flashWriteBasicGroup = actionsGroup.add_argument_group("Прошивка(основні)")
    flashWriteAdvancedGroup = parser.add_argument_group("Прошивка(розширені)")

    firmware_bin_path_help = "Шлях до .bin файлу прошивки. (Однофайловий або для прошивки по Wifi - визначиться автоматично)"
    if(guiMode):
        flashWriteBasicGroup.add_argument('--firmware_bin_path', default=firmware_bin_path_default, type=str, widget="FileChooser", action="store", help=firmware_bin_path_help)
    else:
        flashWriteBasicGroup.add_argument('--firmware_bin_path', default=firmware_bin_path_default, type=str, action="store", help=firmware_bin_path_help)

    if(guiMode):
        flashWriteAdvancedGroup.add_argument('--bootloader_bin_filepath', default=bootloader_bin_path_default, type=str, widget="FileChooser", action="store")
    else:
        flashWriteAdvancedGroup.add_argument('--bootloader_bin_filepath', default=bootloader_bin_path_default, type=str, action="store")

    if(guiMode):
        flashWriteAdvancedGroup.add_argument('--partitions_bin_filepath', default=partitions_bin_path_default, type=str, widget="FileChooser", action="store")
    else:
        flashWriteAdvancedGroup.add_argument('--partitions_bin_filepath', default=partitions_bin_path_default, type=str, action="store")

    flashWriteAdvancedGroup.add_argument('--bootselect_bin_filepath', default=bootselect_bin_path_default, type=str, action="store")

    flashWriteAdvancedGroup.add_argument('--merged_bin_address', default="0x00", type=str, action="store", help="Адреса в flash пам'яті, в яку записувати однофайлову прошивку для Flash Download Tool.")
    flashWriteAdvancedGroup.add_argument('--firmware_address', default="0x10000", type=str, action="store", help="Адреса в flash пам'яті, де починається firmware частина прошивки")
    flashWriteAdvancedGroup.add_argument('--bootloader_address', default="0x1000", type=str, action="store")
    flashWriteAdvancedGroup.add_argument('--partitions_address', default="0x8000", type=str, action="store")
    flashWriteAdvancedGroup.add_argument('--bootselect_address', default="0xe000", type=str, action="store")

    #building bootloader:
    #"C:\Users\1995k\.platformio\penv\Scripts\python.exe" "C:\Users\1995k\.platformio\packages\tool-esptoolpy\esptool.py" --chip esp32 elf2image --flash_mode dio --flash_freq 40m --flash_size 4MB -o .pio\build\esp32dev\bootloader.bin C:\Users\1995k\.platformio\packages\framework-arduinoespressif32\tools\sdk\esp32\bin\bootloader_dio_40m.elf

    actionsGroup.add_argument("--read-mac", action="store_true", default=True, help="Зчитати MAC ID чіпа до і після прошивки")
    actionsGroup.add_argument("--write-flash", action="store_true", default=True, help="Прошити чіп")
    actionsGroup.add_argument("--verify-flash", action="store_true", default=True, help="Перевірити цілістність прошивки в чіпі")
    actionsGroup.add_argument("--erase-flash", action="store_true", default=True, help="Очистити всю flash пам'ять чіпа")
    actionsGroup.add_argument("--read-flash", action="store_true", help="Зчитати всю flash пам'ять в файл read_flash.bin")    
    actionsGroup.add_argument("--merge-bin", action="store_true", help="Зберегти однофайлову прошивку для Flash Download Tool в merged.bin")

    actionsGroup.add_argument("--write-additional-images", action="store_true", default=True, 
                              help="Якщо файл прошивки містить лише firmware(для прошивки по WiFi), то додатково прошити bootloader, partitions, bootselect.")

    actionsGroup.add_argument("--add-to-history-csv", action="store_true", default=True,dest="add_to_history_csv", help="Зберігати історію прошивок.")
    if(not guiMode):
        #Gooey щось не переварює цих негативниз опцій
        actionsGroup.add_argument("--no-add-to-history-csv", action="store_false",  dest="add_to_history_csv", help="Не зберігати історію прошивок.")

    flashWriteBasicGroup.add_argument("--port", default="Auto", type=str, action="store", help="Порт проргаматора")
    flashWriteBasicGroup.add_argument("--baudrate", default=port_speed_default, type=int,  action="store", help="Швидкість порту" + str(port_speeds)) #choices=port_speeds,
    
    flashWriteAdvancedGroup.add_argument("--chip", default="esp32", type=str, action="store", choices=chip_names)
    flashWriteAdvancedGroup.add_argument("--flash-mode", default="dio", type=str, action="store", choices=flash_modes)
    flashWriteAdvancedGroup.add_argument("--flash-frequency", default="40m", type=str, action="store", choices=flash_frequencies)
    flashWriteAdvancedGroup.add_argument("--flash-size", default="detect", type=str, action="store", choices=flash_sizes)

    hackParamsGroup = parser.add_argument_group("не змінювати!")
    hackParamsGroup.add_argument("--ignore-gooey", action="store_true") 
    hackParamsGroup.add_argument("--gui", action="store_true")   
    
    args = parser.parse_args()
    
    parser.parse_args()
    
    
    rawArgsStr = " ".join(sys.argv)
    print("Script ran with cmd-line arguments:   " + rawArgsStr) #Using raw print as backup if logger fails
    
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("myflasher.log"),
            logging.StreamHandler()
        ]
    )
    
    logging.debug("debug")
    logging.info("info")
    logging.warning("warning")
    
    if(args.read_mac):
        success = run_esptool_noexcept("read-mac")
        return 0 if success else 1
    
    if(args.add_to_history_csv):
        print("Adding to history CSV...")
        

#if __name__ == '__main__':
#    main()

######################################
# Code below is GUI wrapper for command line tools.
######################################

guiMode = ('--gui' in sys.argv)

if __name__ == "__main__":    
    if (guiMode):        
        import six
        from gooey import Gooey, GooeyParser
        @Gooey(  
            tabbed_groups=True,
            #default_size=(600, 300),   # starting size of the GUI
            required_cols=3,           # number of columns in the "Required" section
            optional_cols=3,           # number of columns in the "Optional" section)
            header_height=80,
            show_restart_button=True,
            #Stable Gooey v1.0.8 not supports shutdown_signal yet, and always kills subprocesses forcefully.
            # Available in beta. See https://github.com/chriskiehl/Gooey/blob/master/docs/Gracefully-Stopping.md
            #shutdown_signal=signal.CTRL_C_EVENT,
            use_cmd_args=True,
            image_dir="gui_images",
            language_dir="gui_languages",
            language="ukrainian"
            )

        def GUI_main() -> int:
            return main()

        
        ret = GUI_main()
        sys.exit(ret)
    else:
        ret = main()
        sys.exit(ret)