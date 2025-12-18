import sys
import argparse
import signal
import logging
import threading
import time
import esptool

port_speeds = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 8000000, 921600]
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
        
    #mainParamsGroup = parser.add_argument_group("Main")
    
    if(guiMode):
        parser.add_argument('--bin_filepath', default="None", type=str, widget="FileChooser", action="store")
    else:
        parser.add_argument('--bin_filepath', default="None", type=str, action="store")
        
    parser.add_argument("--read-mac", action="store_true", help="Read mac")
    parser.add_argument("--port", default="Auto", type=str, action="store", help="Custom port")
    parser.add_argument("--baudrate", default=9600, type=int,  action="store", help=str(port_speeds)) #choices=port_speeds,

    
    hackParamsGroup = parser.add_argument_group("hacks, do not change.")
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
            #tabbed_groups=True,
            #default_size=(1100, 600),   # starting size of the GUI
            #required_cols=4,           # number of columns in the "Required" section
            #optional_cols=4,           # number of columns in the "Optional" section)
            #header_height=20,
            show_restart_button=False,
            #Stable Gooey v1.0.8 not supports shutdown_signal yet, and always kills subprocesses forcefully.
            # Available in beta. See https://github.com/chriskiehl/Gooey/blob/master/docs/Gracefully-Stopping.md
            #shutdown_signal=signal.CTRL_C_EVENT,
            use_cmd_args=True)

        def GUI_main() -> int:
            return main()

        
        ret = GUI_main()
        sys.exit(ret)
    else:
        ret = main()
        sys.exit(ret)