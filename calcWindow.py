from tkinter import Tk, ttk, StringVar, Text
import re

from cannonConstants import cardinalDir
from ballisticsCalc import calculateLaunchParameters
import numpy as np


# Wrapper class for 3 coords
class coordinateInput(ttk.Frame):
    def __init__(self, master, *args, **kwargs):
        ttk.Frame.__init__(self, master, *args, **kwargs)
        
        def validateInt(inStr) -> bool:
            return re.match("^[+-]?[0-9]+$", inStr) is not None
        wrappedCheck = (self.register(validateInt), "%P")
        
        self.coordX = StringVar(value=str(0))
        self.coordY = StringVar(value=str(0))
        self.coordZ = StringVar(value=str(0))
        
        ttk.Label(self, text="X:").grid(column=1, row=1)
        ttk.Entry(self, textvariable=self.coordX, validate="key", validatecommand=wrappedCheck).grid(column=2, row=1)
        
        ttk.Label(self, text="Y:").grid(column=3, row=1)
        ttk.Entry(self, textvariable=self.coordY, validate="key", validatecommand=wrappedCheck).grid(column=4, row=1)
        
        ttk.Label(self, text="Z:").grid(column=5, row=1)
        ttk.Entry(self, textvariable=self.coordZ, validate="key", validatecommand=wrappedCheck).grid(column=6, row=1)
        
        self.columnconfigure(2, weight=1)
        self.columnconfigure(4, weight=1)
        self.columnconfigure(6, weight=1)
        self.rowconfigure(1, weight=1)
        
        for child in self.winfo_children():
            child.grid_configure(padx=1, pady=1)
    
    def getCoords(self) -> list[int]:
        return [int(self.coordX.get()), int(self.coordY.get()), int(self.coordZ.get())]


def updateResult(*args):
    cannonDir = cardinalDir[cardDir.get().upper()]
    cannonOrigin = np.array(originCoords.getCoords())
    targetPos = np.array(targetCoords.getCoords())
    quadId, flyTime, firstStack, lastStack, actualPos = calculateLaunchParameters(cannonDir, cannonOrigin, targetPos)
    quadDecode = ["Bottom-Left", "Top-left", "Top-Right", "Bottom-Right"]
    resultPrint = (
        f"Target position: {str(targetPos)}\n"
        f"Sector in UI: {quadDecode[quadId.value]}\n"
        f"First charge stack size: {firstStack}\n"
        f"Last charge stack size: {lastStack}\n"
        f"Nearest hit position: {str(actualPos)}; Flight time: {flyTime} ticks"
    )
    resultText["state"] = "normal"
    resultText.delete(1.0, 1.0e6)
    resultText.insert(1.0, resultPrint)
    resultText["state"] = "disabled"
    

root = Tk()
root.title("Wind charge pearl cannon calculator")
root.columnconfigure(1, weight=1)
root.rowconfigure(1, weight=1)
mainframe = ttk.Frame(root, padding=(3, 3, 3, 3))
mainframe.grid(row=1, column=1, sticky="NW")
mainframe.columnconfigure(2, weight=1)

# Cannon position section
ttk.Label(mainframe, text="Cannon origin settings").grid(column=1, row=11, columnspan=2)

ttk.Label(mainframe, text="Coordinate").grid(column=1, row=12, sticky="E")
originCoords = coordinateInput(mainframe)
originCoords.grid(column=2, row=12)

ttk.Label(mainframe, text="Facing direction").grid(column=1, row=13, sticky="E")
cardDir = StringVar(value=cardinalDir.SOUTH.name)
dirSelect = ttk.Combobox(mainframe, textvariable=cardDir)
dirSelect.grid(column=2, row=13, sticky="NW")
dirSelect["values"] = (cardinalDir.NORTH.name, cardinalDir.SOUTH.name, cardinalDir.EAST.name, cardinalDir.WEST.name)
dirSelect.state(["readonly"])

# Target select section
ttk.Separator(mainframe, orient="horizontal").grid(column=1, row=20, columnspan=2, sticky="EW")
ttk.Label(mainframe, text="Target selection").grid(column=1, row=21, columnspan=2)

ttk.Label(mainframe, text="Coordinate").grid(column=1, row=22, sticky="E")
targetCoords = coordinateInput(mainframe)
targetCoords.grid(column=2, row=22)

# Result display section
ttk.Separator(mainframe, orient="horizontal").grid(column=1, row=30, columnspan=2, sticky="EW")
ttk.Label(mainframe, text="Results").grid(column=1, row=31, columnspan=2)

resultFrame = ttk.Frame(mainframe, padding=(3, 3, 3, 3))
resultFrame.grid(column=1, row=32, sticky="NWE", columnspan=2)
resultFrame.columnconfigure(1, weight=3)
resultFrame.columnconfigure(2, weight=1)

resultText = Text(resultFrame, height=5, width=50)
resultText.grid(column=1, row=1)
resultText.insert(1.0, "Press Update to apply settings")
resultText["state"] = "disabled"

ttk.Button(resultFrame, text="Update", command=updateResult).grid(column=2, row=1)

# Global padding
for child in mainframe.winfo_children(): 
    child.grid_configure(padx=3, pady=3)

root.mainloop()

# This seems to work. TODO - polish
#  (format coordinate output, expand result field)
#  (add some info popups?)
