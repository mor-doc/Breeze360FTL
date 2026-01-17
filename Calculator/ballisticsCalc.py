from numpy import ndarray, array, deg2rad, rad2deg, eye, sin, cos, matmul, transpose, vstack, arctan2, mod
from numpy.linalg import inv, norm
from scipy.optimize import fsolve
from enum import Enum

from cannonConstants import *

# More readable indexing for launch area quadrants. 
# Directions are in cannon-local frame
class launchQuadId(Enum):
    NE = 0
    SE = 1
    SW = 2
    NW = 3

def rotateCoord(startDir: cardinalDir, endDir: cardinalDir, coordVec: ndarray) -> ndarray:
    """
    Rotate coordinate by azimuth from starting to final cardinal direction. 
    Example:
        rotateCoord(NORTH, EAST, [1, 0, 0]) => [0, 0, 1]
    TODO - test use on array of vectors (Nx3 matrix)

    Args:
        startDir (cardinalDir): initial facing direction
        endDir (cardinalDir): final facing direction
        coordVec (ndarray): 1x3 vector to be rotated

    Returns:
        ndarray: 1x3 vector facing new direction
    """
    angleCCW = (endDir.value - startDir.value) * 90
    angleRad = deg2rad(angleCCW)
    rotMatrix = eye(3)
    rotMatrix[0][0] = rotMatrix[2][2] = cos(angleRad)
    rotMatrix[0][2] = sin(angleRad)
    rotMatrix[2][0] = -sin(angleRad)
    return matmul(coordVec, rotMatrix)



# Only valid for ender pearls due to ticking order
def projectileTickStep(pos, vel):
    # acceleration
    newVel = vel + array([0.0, -0.03, 0.0])
    # drag
    newVel *= 0.99
    # position update
    newPos = pos + newVel
    return (newPos, newVel)

def pearlInitVelFromEndPos(tick: int, displacement: ndarray) -> ndarray:
    """
    Get initial velocity to get required ender pearl displacement after some time
    (see wiki for formula)

    Args:
        tick (int): flight time from trajectory start in gameticks
        displacement (ndarray): target displacement as 1x3 vector

    Returns:
        ndarray: initial velocity as 1x3 vector
    """
    
    d = 0.9900000095367432
    a = array([0.0, -0.03, 0.0])
    return (1 - d) / (d * (1 - pow(d, tick))) * (displacement - d * tick * a / (1 - d)) + (d / (1 - d) * a)

def pearlPosFromInitVel(tick: float, vel0: ndarray) -> ndarray:
    """
    Get ender pearl displacement from initial velocity after some time
    (see wiki for formula)

    Args:
        tick (float): time from trajectory start in gameticks
        vel0 (ndarray): initial velocity as 1x3 vector

    Returns:
        ndarray: displacement relative to starting point as 1x3 vector
    """

    d = 0.9900000095367432
    a = array([0.0, -0.03, 0.0])
    return (d * (1 - pow(d, tick))) / (1 - d) * (vel0 - d / (1 - d) * a) + (d * tick * a / (1 - d))

def getExplosionMatrix(velA:ndarray, velB:ndarray) -> ndarray:
    """
    Get E matrix from two 3D explosion velocity vectors
    (see tutorial wiki page)

    Args:
        velA (ndarray): velocity from first explosion as 1x3 vector
        velB (ndarray): velocity from second explosion as 1x3 vector

    Returns:
        ndarray: 2x3 E matrix
    """
    
    velMatrix = transpose(vstack((velA, velB)))
    A = matmul(transpose(velMatrix), velMatrix)
    B = inv(A)
    C = matmul(B, transpose(velMatrix))
    return C

def getChargePearlPushVelocity(explosionCenterPos: ndarray, pearlFeetPos: ndarray) -> ndarray:
    """
    Calculate impulse to ender pearl from one wind charge explosion. 
    Assumes 100% exposure 
    (see Explosion wiki page for formulas)

    Args:
        explosionCenterPos (ndarray): position of wind charge explosion as 1x3 vector
        pearlFeetPos (ndarray): position of ender pearl feet (reported position) as 1x3 vector

    Returns:
        ndarray: velocity change as 1x3 vector (away from wind charge)
    """
    
    feetDist = pearlFeetPos - explosionCenterPos
    PearlEyeHeight = 0.2125
    WindChargePower = 3.0
    exposure = 1.0    
    magnitude = (1 - norm(feetDist) / (2 * WindChargePower)) * exposure
    eyeVector = feetDist + array([0.0, PearlEyeHeight, 0.0])
    velocityVector = eyeVector / norm(eyeVector) * magnitude
    return velocityVector

def findChargeAmount(velA: ndarray, velB: ndarray, targetOffs: ndarray) -> ndarray:
    """
    Solve for wind charge stack sizes and flight time

    Args:
        velA (ndarray): velocity added to ender pearl from one wind charge in position A. Format - 1x3 vector
        velB (ndarray): velocity added to ender pearl from one wind charge in position B. Format - 1x3 vector
        targetOffs (ndarray): relative offset from initial pearl position to target

    Returns:
        ndarray: nearest solution as 1x3 vector of floats. 
            Element 0 - flight time (in gameticks). Element 1 - size of charge stack A. Element 2 - size of charge stack B.
    """
    
    # idea - use gameticks as another variable, 3 total. Return full pos error
    def optimizeFunc(x):
        tick, amtA, amtB = x
        velVector = amtA * velA + amtB * velB
        velVector += pearlInitialVelocity
        pearlPos = pearlPosFromInitVel(tick, velVector)
        posError = targetOffs - pearlPos
        return posError
    result = fsolve(optimizeFunc, [1.0e9, 0, 0])
    
    return result # type: ignore

def getLocalQuadData(targetOffs : ndarray) -> tuple[launchQuadId, ndarray, ndarray]:
    """
    Get shooting quadrant info from target position offset

    Args:
        targetOffs (ndarray): target position relative to acceleration zone in cannon-local frame

    Returns:
        tuple[launchQuadId, ndarray, ndarray]: id of quad for UI, position of first charge stack, position of last charge stack
    """
    
    # Tested, adjusted, seems to give correct results.
    
    chargePearlVectors = chargePositions - pearlPosition
    
    # Add target displacement into same array for batch processing
    allVectorArr = vstack((chargePearlVectors, -targetOffs))
    chargeAngles = arctan2(-allVectorArr[:, 2], allVectorArr[:, 0])
    simpleAnglesDeg = mod(rad2deg(chargeAngles) + 360, 360)
    targetAngleDeg = simpleAnglesDeg[4]
    
    # Find nearest angle in CCW direction
    ccwNearestIndex = 0
    # Get all angles bigger (more CCW) than target angle
    cwAngles = [(i, ang) for i, ang in enumerate(simpleAnglesDeg[0:4]) if ang > targetAngleDeg]
    # Get nearest CCW angle to target
    if len(cwAngles) == 0:
        ccwNearestIndex = 0
    else:
        ccwNearestIndex = min(cwAngles, key=lambda x: x[1])[0]
    
    cwNearestIndex = (ccwNearestIndex + 1) % 4
    quadId = launchQuadId(cwNearestIndex)
    firstStackCoord = chargePositions[max(cwNearestIndex, ccwNearestIndex)]
    secondStackcoord = chargePositions[min(cwNearestIndex, ccwNearestIndex)]
    
    return (quadId, firstStackCoord, secondStackcoord)

def calculateLaunchParameters(cannonDir : cardinalDir, cannonPos: ndarray, targetPos: ndarray) -> tuple[launchQuadId, int, int, int, ndarray]:
    """
    Calculate launch parameters for the cannon to hit near the target

    Args:
        cannonDir (cardinalDir): cardinal direction taken looking at item frame
        cannonPos (ndarray): absolute position of block behind item frame as 1x3 vector
        targetPos (ndarray): absolute target position as 1x3 vector

    Returns:
        tuple[launchQuadId, int, int, int, ndarray]: launch parameters:
            - index of quadrant to select with item frame (0 is bottom-left, 3 is bottom-right)
            - flight time in gameticks
            - number of wind charges in first stack
            - number of wind charges in last stack
            - nearest possible coordinates to target
    """

    shootingPos = cannonPos + rotateCoord(defaultFacingDir, cannonDir, itemToOriginOffset)
    globalTargetOffset = targetPos - shootingPos
    localTargetOffset = rotateCoord(cannonDir, defaultFacingDir, globalTargetOffset)


    quadId, stackPosA, stackPosB = getLocalQuadData(localTargetOffset)
    velA = getChargePearlPushVelocity(stackPosA, pearlPosition)
    velB = getChargePearlPushVelocity(stackPosB, pearlPosition)
    idealCannonSetting = findChargeAmount(velA, velB, localTargetOffset)
    # Get realistic values, check rounding error
    ticks, chargesA, chargesB = idealCannonSetting.round()
    velVector = chargesA * velA + chargesB * velB
    actualLocalOffs = pearlPosFromInitVel(ticks, velVector)
    actualLandingPos = shootingPos + rotateCoord(defaultFacingDir, cannonDir, actualLocalOffs)
    
    return (quadId, ticks, chargesA, chargesB, actualLandingPos)