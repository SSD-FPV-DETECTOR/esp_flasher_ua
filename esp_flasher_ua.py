from asyncio.log import logger
import sys
import argparse
import signal
import logging
import threading
import time
import os

import esptool
import esptool.cmds
from esptool import ESPLoader
#from click.testing import CliRunner
#from esptool import cli
#from esptool import prepare_esp_object
import EsptoolWrapper
from esptool.bin_image import (
    ESP8266ROMFirmwareImage,
    ESP8266V2FirmwareImage,
    ESP8266V3FirmwareImage,
)

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
history_csv_path_default = "flash_history.csv"

before_reset_names = ["default-reset", "usb-reset", "no-reset", "no-reset-no-sync"]
after_reset_names = ["hard-reset", "soft-reset", "no-reset", "no-reset-stub", "watchdog-reset"]



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
    flashWriteBasicGroup = parser.add_argument_group("Прошивка(основні)")
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

    #building partiotoins bins
    #"C:\Users\1995k\.platformio\penv\Scripts\python.exe" "C:\Users\1995k\.platformio\packages\framework-arduinoespressif32\tools\gen_esp32part.py" -q C:\Users\1995k\.platformio\packages\framework-arduinoespressif32\tools\partitions\default.csv .pio\build\esp32dev\partitions.bin
    
    actionsGroup.add_argument("--read-mac", action="store_true", default=True, help="Зчитати MAC ID чіпа до і після прошивки")
    actionsGroup.add_argument("--write-flash", action="store_true", help="Прошити чіп")
    actionsGroup.add_argument("--verify-flash", action="store_true", help="Перевірити цілістність прошивки в чіпі")
    actionsGroup.add_argument("--erase-all", action="store_true", help="Очистити всю flash пам'ять чіпа")
    actionsGroup.add_argument("--read-flash", action="store_true", help="Зчитати всю flash пам'ять в файл read_flash.bin")    
    actionsGroup.add_argument("--merge-bin", action="store_true", help="Зберегти однофайлову прошивку для Flash Download Tool в merged.bin")

    actionsGroup.add_argument("--write-additional-images", action="store_true",# default=True, 
                              help="Якщо файл прошивки містить лише firmware(для прошивки по WiFi), то додатково прошити bootloader, partitions, bootselect.")

    actionsGroup.add_argument("--add-to-history-csv", action="store_true", default=True,dest="add_to_history_csv", help="Зберігати історію прошивок.")
    if(not guiMode):
        #Gooey щось не переварює цих негативниз опцій
        actionsGroup.add_argument("--no-add-to-history-csv", action="store_false",  dest="add_to_history_csv", help="Не зберігати історію прошивок.")
        actionsGroup.add_argument("--no-read-mac", action="store_false",  dest="read_mac", help="Не зчитувати MAC ID чіпа.")
        actionsGroup.add_argument("--no-write-flash", action="store_false",  dest="write_flash", help="Не прошивати чіп.")
        actionsGroup.add_argument("--no-verify-flash", action="store_false",  dest="verify_flash", help="Не перевіряти цілістність прошивки в чіпі.")
        actionsGroup.add_argument("--no-erase-all", action="store_false",  dest="erase_all", help="Не очищати всю flash пам'ять чіпа.")
        actionsGroup.add_argument("--no-write-additional-images", action="store_false",  dest="write_additional_images", help="Прошити лише firmware.")

    flashWriteBasicGroup.add_argument("--port", default="auto", type=str, action="store", help="Порт проргаматора")
    flashWriteBasicGroup.add_argument("--baudrate", default=port_speed_default, type=int,  action="store", help="Швидкість порту" + str(port_speeds)) #choices=port_speeds,
    
    flashWriteAdvancedGroup.add_argument("--chip", default="esp32", type=str, action="store", choices=chip_names)
    flashWriteAdvancedGroup.add_argument("--flash-mode", default="dio", type=str, action="store", choices=flash_modes)
    flashWriteAdvancedGroup.add_argument("--flash-frequency", default="40m", type=str, action="store", choices=flash_frequencies)
    flashWriteAdvancedGroup.add_argument("--flash-size", default="detect", type=str, action="store", choices=flash_sizes)

    flashWriteAdvancedGroup.add_argument("--after", default="hard-reset", type=str, action="store", choices=after_reset_names, help="Дія після прошивки")
    flashWriteAdvancedGroup.add_argument("--before", default="default-reset", type=str, action="store", choices=before_reset_names, help="Дія перед прошивкою")

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
    

    if(args.add_to_history_csv):
        with open(history_csv_path_default, "a") as historyFile:
            from datetime import datetime
            now = datetime.now()
            timestampStr = now.strftime("%d-%m-%Y %H:%M:%S")
            firmware_bin_path = os.path.normpath(args.firmware_bin_path)            
            rawArgsStr = " ".join(sys.argv[1:])

            historyFile.write(f'\n"{timestampStr}","{rawArgsStr}","{firmware_bin_path}",')

    actionsResult = DoActions(args)
    if(actionsResult and args.add_to_history_csv):
        with open(history_csv_path_default, "a") as historyFile:
            historyFile.write(f'"Success"')

        
def DoActions(args) -> bool:

    #Before conection, verity files:
    
    if(args.write_flash or args.verify_flash):
        #Verify files
        logging.info("Перевірка вибраних файлів прошивки...")

        firmware_bin_path = os.path.normpath(args.firmware_bin_path)

        if(not os.path.isfile(firmware_bin_path)):
            logging.error(f"Файл прошивки не знайдено: {firmware_bin_path}")
            return False

        addr_data: list[tuple[int, str]] = []

        isImage = IsImage(firmware_bin_path)

        if(not isImage):
            firmware_address = int(args.merged_bin_address, 0)
            logging.info("Файл прошивки не є образом, вважаємо що це однофайлова прошивка для Flash Download Tool, будемо писати її в адрес 0x{:02x}.".format(firmware_address))
            addr_data.append((firmware_address, firmware_bin_path))
        else:
            firmware_address = int(args.firmware_address, 0)
            addr_data.append((firmware_address, firmware_bin_path))        

            if(args.write_additional_images):
                bootloader_bin_filepath = os.path.normpath(args.bootloader_bin_filepath)
                partitions_bin_filepath = os.path.normpath(args.partitions_bin_filepath)
                bootselect_bin_filepath = os.path.normpath(args.bootselect_bin_filepath)

                bootloader_address = int(args.bootloader_address, 0)
                partitions_address = int(args.partitions_address, 0)
                bootselect_address = int(args.bootselect_address, 0)
                
                if(not os.path.isfile(bootloader_bin_filepath)):
                    logging.error(f"Файл бутлоадера не знайдено: {bootloader_bin_filepath}")
                    return False

                if(not os.path.isfile(partitions_bin_filepath)):
                    logging.error(f"Файл partitions не знайдено: {partitions_bin_filepath}")
                    return False

                if(not os.path.isfile(bootselect_bin_filepath)):
                    logging.error(f"Файл bootselect не знайдено: {bootselect_bin_filepath}")
                    return False

                addr_data.append((bootloader_address, bootloader_bin_filepath))
                addr_data.append((partitions_address, partitions_bin_filepath))
                addr_data.append((bootselect_address, bootselect_bin_filepath))

        addr_data.sort(key=lambda t: t[0]) #Sort by address!
        
        logging.info("Наступні файли будуть прошиті по наступним адресам:")
        for addr, data in addr_data:
            logging.info("  0x{:06X} : {}".format(addr, data))
        logging.info("----------------------")


    portStr = args.port if len(args.port) and args.port != "auto" else None

    esp: ESPLoader = EsptoolWrapper.prepare_esp_object(baudrate=args.baudrate,
                                                        port=portStr,
                                                        port_filters=[],
                                                        chip=args.chip,
                                                        before=args.before,
                                                        trace = False,
                                                        no_stub=False)
    if(esp is None):
        logging.error("Не вдалось підключитись до пристрою.")
        return False
    
    macStr = ""
    if(args.read_mac):
        mac = esp.read_mac()
        macStr = "{:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}".format(*mac)
        logging.info("MAC адреса чіпа: " + macStr)        
        if(args.add_to_history_csv):
            with open(history_csv_path_default, "a") as historyFile:
                historyFile.write(f'"{macStr}",')

    if(args.erase_all):
        logging.info("Стираємо повністю флеш, це може зайняти до хвилини...")
        #esp.erase_flash()
        esptool.cmds.erase_flash(esp, force=False)
    
    if(args.write_flash):
        logging.info("Стартуємо прошивку...")
        esptool.cmds.write_flash(
                                esp,
                                addr_data,
                                flash_mode=args.flash_mode,
                                flash_freq=args.flash_frequency,
                                flash_size=args.flash_size,
                                erase_all=False
                                )
        
    if(args.verify_flash and not args.write_flash):
        #Write does verify anyway, so only verify if not writing
        logging.info("Перевіряємо цілісність прошивки...")
        esptool.cmds.verify_flash(esp,
                                    addr_data,
                            flash_mode=args.flash_mode,
                            flash_freq=args.flash_frequency,
                            flash_size=args.flash_size)
    
    if(args.read_flash):
        logging.info("Зчитуємо флеш в read_flash.bin ...")
        esptool.cmds.read_flash(esp, 0x00000, esp.flash_size_bytes(), "read_flash.bin")

    logging.info("Перезавантажуємо чіп %s ..." % args.after)
    esptool.cmds.reset_chip(esp, args.after)        

    return True

def IsImage(path: os.PathLike) -> bool:
    try:
        with open(path, "rb") as in_file:
            magic_byte = in_file.read(1)[0]

            if magic_byte in [
                ESPLoader.ESP_IMAGE_MAGIC,
                ESP8266V2FirmwareImage.IMAGE_V2_MAGIC,
                ]:
                return True
    except Exception as e:
        logging.error(f"Error reading image file: {str(e)}")

    return False




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