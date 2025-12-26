import numpy as np
from enum import Enum

# Enum for Minecraft world directions. East is +X, South is +Z.
class cardinalDir(Enum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

# Array of wind charge positions relative to launch zone center. 
# Assumes that charge stacks enter in bottom-left corner (from East / positive X). 
chargePositions = np.array([
    [+0.83375, 0.75, +0.16625],      # earliest pos in spiral
    [-0.16625, 0.75, +0.84375], 
    [-0.84375, 0.75, -0.16625], 
    [+0.16625, 0.75, -0.84375]       # latest pos in spiral (gets inside 1st block)
    ])

# Facing direction of cannon in default orientation. 
# Taken by looking at item frame
defaultFacingDir = cardinalDir.WEST

# Offset from block behind item frame to center of 2x2 explosion area
# In default facing direction, areaPos = itemFramePos + offset
itemToOriginOffset = np.array([-28, 14, -18])

# Coordinate of ender pearl (feet pos) at the moment of explosion, relative to 2x2 area center. 
# Same orientation as wind charge coordinates
pearlPosition = np.array([-0.0625, 0.540222006, +0.0625])

# Pearl velocity at the moment of explosion
pearlInitialVelocity = np.array([0.0, -0.00372668019444022, 0.0])
# (test)
# -0.00372668019444022
# -0.0333894137141385
