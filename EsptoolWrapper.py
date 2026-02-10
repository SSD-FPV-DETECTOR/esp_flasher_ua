import esptool
import logging
import sys

from esptool import parse_port_filters, get_port_list, connect_loop, get_default_connected_device
from esptool import read_mac
from esptool import FatalError, NotImplementedInROMError

from esptool.loader import (
    DEFAULT_CONNECT_ATTEMPTS,
    DEFAULT_OPEN_PORT_ATTEMPTS,
    StubFlasher,
    ESPLoader,
    list_ports,
)

def prepare_esp_object(baudrate:int,
                        port:str = None,
                        port_filters:tuple[str]=[],
                        chip:str="auto",
                        before:str="default-reset",
                        trace:bool=False,
                        no_stub:bool=False):
    """Prepare ESP object for operation"""

    #StubFlasher.set_stub_subdir(ctx.obj["stub_version"])
    # Commands that require an ESP object (flash read/write, etc.)
    # 1) Get the ESP object
    #######################

    if before != "no-reset-no-sync":
        initial_baud = min(
            ESPLoader.ESP_ROM_BAUD, baudrate
        )  # don't sync faster than the default baud rate
    else:
        initial_baud = baudrate

    if port is None:
        #filters = parse_port_filters(port_filters)
        ser_list = GetPortsList()
        logging.info(f"Found {len(ser_list)} serial ports...")
    else:
        ser_list = [port]

    open_port_attempts = DEFAULT_OPEN_PORT_ATTEMPTS
    try:
        open_port_attempts = int(open_port_attempts)
    except ValueError:
        raise SystemExit("Invalid value for ESPTOOL_OPEN_PORT_ATTEMPTS.")

    esp: ESPLoader = None
    
    if open_port_attempts != 1:
        if port is None or chip == "auto":
            logging.warning(
                "The ESPTOOL_OPEN_PORT_ATTEMPTS (open_port_attempts) option "
                "can only be used with --port and --chip arguments."
            )
        else:
            esp = esp or connect_loop(
                port,
                initial_baud,
                chip,
                open_port_attempts,
                trace,
                before,
            )

    connect_attempts = DEFAULT_CONNECT_ATTEMPTS
    esp = esp or get_default_connected_device(
        ser_list,
        port=port,
        connect_attempts=connect_attempts,
        initial_baud=initial_baud,
        chip=chip,
        trace=trace,
        before=before,
    )

    if esp is None:
        raise FatalError(
            "Could not connect to an Espressif device "
            f"on any of the {len(ser_list)} available serial ports."
        )

    logging.info(f"Connected to {esp.CHIP_NAME} on {esp._port.port}:")

    # 2) Print the chip info
    ########################

    if esp.secure_download_mode:
        logging.info(f"{'Chip type:':<20}{esp.CHIP_NAME} in Secure Download Mode")
    else:
        logging.info(f"{'Chip type:':<20}{esp.get_chip_description()}")
        logging.info(f"{'Features:':<20}{', '.join(esp.get_chip_features())}")
        logging.info(f"{'Crystal frequency:':<20}{esp.get_crystal_freq()}MHz")
        usb_mode = esp.get_usb_mode()
        if usb_mode is not None:
            logging.info(f"{'USB mode:':<20}{usb_mode}")
        esptool.read_mac(esp)
    

    # 3) Perform sanity checks
    ##########################

    #if esp.secure_download_mode and ctx.obj["invoked_subcommand"] not in (
    #    "get-security-info",
    #    "write-flash",
    #    "erase-region",
    #):
    #    raise FatalError(
    #        f"The '{ctx.obj['invoked_subcommand']}' command is not available "
    #        "in Secure Download Mode."
    #    )

    # 4) Upload the stub flasher
    ############################

    if not no_stub:
        esp = esptool.run_stub(esp)

    # 5) Configure the baud rate and voltage regulator
    ##################################################

    #if ctx.obj["override_vddsdio"]:
    #    esp.override_vddsdio(ctx.obj["override_vddsdio"])

    if baudrate > initial_baud:
        try:
            esp.change_baud(baudrate)
        except NotImplementedInROMError:
            logging.warning(
                f"ROM doesn't support changing baud rate. "
                f"Keeping initial baud rate {initial_baud}."
            )

    # 6) Prepare to run the operation
    #################################
    # Running operation is done inside each command function, as they have different
    # arguments and behaviour
    # Prepare object for operation (commands)
    #ctx.obj["esp"] = esp
    #log.print()

    # 7) Attach the onboard/external flash chip and perform command
    ###############################################################
    # This will follow in command-specific functions or argument processing decorators
    # After the command is done (either successfully or with an error), the following
    # teardown function will be called

    return esp

    #@ctx.call_on_close
    def teardown():
        """Common teardown for all commands with chip - reset chip and close port"""
        # 8) Close all open files
        #########################
        for f in getattr(ctx, "_open_files", []):
            f.close()

        # 9) Reset the chip
        ###################
        log.print()
        # Handle post-operation behaviour (reset or other)
        if ctx.obj["invoked_subcommand"] == "load-ram":
            # the ESP is now running the loaded image, so let it run
            log.print("Exiting immediately.")
        else:
            reset_chip(esp, ctx.obj["after"])

        # 10) Finish and close the port
        ##############################

        if not ctx.obj["external_esp"]:
            esp._port.close()

def GetPortsList() -> list[str]:
    #Copypasted from ESPTool get_ports_list
    if list_ports is None:
        raise FatalError(
            "Listing all serial ports is currently not available. "
            "Please try to specify the port when running esptool or update "
            "the pyserial package to the latest version."
        )
    portsUnfiltered = list_ports.comports()
    portsUnsorted = []
    for port in portsUnfiltered:
        if sys.platform == "darwin" and port.device.endswith( #MacOs
            ("Bluetooth-Incoming-Port", "wlan-debug")
        ):
            continue
        portsUnsorted.append(port)

    #def port_sort_key(a, b) -> int:
    #    aBluetooth = 1 if "bluetooth" in a.device.lower() and "bluetooth" not in b.device else 0
    #    bBluetooth = 1 if "bluetooth" in b.device.lower() and "bluetooth" not in a.device else 0
    #    return (aBluetooth - bBluetooth) 

    #Bluetooth ports go last.
    portsUnsorted.sort(key=lambda port: ( not "bluetooth" in port.description.lower(), port.device ))

    portNames = []
    for port in portsUnsorted:
        portNames.append(port.device)

    return portNames