#from escpos.printer import Usb
import escpos.printer

""" Seiko Epson Corp. Receipt Printer (EPSON TM-T88III) """
#p = Usb(0x04b8, 0x0202, 0, profile="TM-T88III")
p = escpos.printer.Serial("/dev/ttyUSB0", 38400)
p.text("Hello World\n")
p.text("FUCK!!!\n")
p.text("FUCK!!!\n")
p.text("FUCK!!!\n")
p.text("FUCK!!!\n")
p.text("FUCK!!!\n")
p.text("FUCK!!!\n")
#p.image("assets/grey256V2.png")
p.barcode('1324354657687', 'EAN13', 64, 2, '', '')
p.cut()
