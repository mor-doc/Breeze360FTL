import numpy as np
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

def rotateCoord(startDir: cardinalDir, endDir: cardinalDir, coordVec: np.ndarray) -> np.ndarray:
    """
    Rotate coordinate by azimuth from starting to final cardinal direction. 
    Example:
        rotateCoord(NORTH, EAST, [1, 0, 0]) => [0, 0, 1]
    TODO - test use on array of vectors (Nx3 matrix)

    Args:
        startDir (cardinalDir): initial facing direction
        endDir (cardinalDir): final facing direction
        coordVec (np.ndarray): 1x3 vector to be rotated

    Returns:
        np.ndarray: 1x3 vector facing new direction
    """
    angleCCW = (endDir.value - startDir.value) * 90
    angleRad = np.deg2rad(angleCCW)
    rotMatrix = np.eye(3)
    rotMatrix[0][0] = rotMatrix[2][2] = np.cos(angleRad)
    rotMatrix[0][2] = np.sin(angleRad)
    rotMatrix[2][0] = -np.sin(angleRad)
    return np.matmul(coordVec, rotMatrix)



# # Only valid for ender pearls due to ticking order
# def projectileTickStep(pos, vel):
#     # acceleration
#     vel += np.array([0.0, -0.03, 0.0])
#     # drag
#     vel *= 0.99
#     # position update
#     pos += vel
#     return (pos, vel)

def pearlInitVelFromEndPos(tick: int, displacement: np.ndarray) -> np.ndarray:
    """
    Get initial velocity to get required ender pearl displacement after some time
    (see wiki for formula)

    Args:
        tick (int): flight time from trajectory start in gameticks
        displacement (np.ndarray): target displacement as 1x3 vector

    Returns:
        np.ndarray: initial velocity as 1x3 vector
    """
    
    d = 0.9900000095367432
    a = np.array([0.0, -0.03, 0.0])
    return (1 - d) / (d * (1 - pow(d, tick))) * (displacement - d * tick * a / (1 - d)) + (d / (1 - d) * a)

def pearlPosFromInitVel(tick: float, vel0: np.ndarray) -> np.ndarray:
    """
    Get ender pearl displacement from initial velocity after some time
    (see wiki for formula)

    Args:
        tick (float): time from trajectory start in gameticks
        vel0 (np.ndarray): initial velocity as 1x3 vector

    Returns:
        np.ndarray: displacement relative to starting point as 1x3 vector
    """

    d = 0.9900000095367432
    a = np.array([0.0, -0.03, 0.0])
    return (d * (1 - pow(d, tick))) / (1 - d) * (vel0 - d / (1 - d) * a) + (d * tick * a / (1 - d))

def getExplosionMatrix(velA:np.ndarray, velB:np.ndarray) -> np.ndarray:
    """
    Get E matrix from two 3D explosion velocity vectors
    (see tutorial wiki page)

    Args:
        velA (np.ndarray): velocity from first explosion as 1x3 vector
        velB (np.ndarray): velocity from second explosion as 1x3 vector

    Returns:
        np.ndarray: 2x3 E matrix
    """
    
    velMatrix = np.transpose(np.vstack((velA, velB)))
    A = np.matmul(np.transpose(velMatrix), velMatrix)
    B = np.linalg.inv(A)
    C = np.matmul(B, np.transpose(velMatrix))
    return C

def getChargePearlPushVelocity(explosionCenterPos: np.ndarray, pearlFeetPos: np.ndarray) -> np.ndarray:
    """
    Calculate impulse to ender pearl from one wind charge explosion. 
    Assumes 100% exposure 
    (see Explosion wiki page for formulas)

    Args:
        explosionCenterPos (np.ndarray): position of wind charge explosion as 1x3 vector
        pearlFeetPos (np.ndarray): position of ender pearl feet (reported position) as 1x3 vector

    Returns:
        np.ndarray: velocity change as 1x3 vector (away from wind charge)
    """
    
    feetDist = pearlFeetPos - explosionCenterPos
    PearlEyeHeight = 0.2125
    WindChargePower = 3.0
    exposure = 1.0    
    magnitude = (1 - np.linalg.norm(feetDist) / (2 * WindChargePower)) * exposure
    eyeVector = feetDist + np.array([0.0, PearlEyeHeight, 0.0])
    velocityVector = eyeVector / np.linalg.norm(eyeVector) * magnitude
    return velocityVector

def findChargeAmount(velA: np.ndarray, velB: np.ndarray, targetOffs: np.ndarray) -> np.ndarray:
    """
    Solve for wind charge stack sizes and flight time

    Args:
        velA (np.ndarray): velocity added to ender pearl from one wind charge in position A. Format - 1x3 vector
        velB (np.ndarray): velocity added to ender pearl from one wind charge in position B. Format - 1x3 vector
        targetOffs (np.ndarray): relative offset from initial pearl position to target

    Returns:
        np.ndarray: nearest solution as 1x3 vector of floats. 
            Element 0 - flight time (in gameticks). Element 1 - size of charge stack A. Element 2 - size of charge stack B.
    """
    
    # idea - use gameticks as another variable, 3 total. Return full pos error
    def optimizeFunc(x):
        tick, amtA, amtB = x
        velVector = amtA * velA + amtB * velB
        pearlPos = pearlPosFromInitVel(tick, velVector)
        posError = targetOffs - pearlPos
        return posError
    result = fsolve(optimizeFunc, [1, 0, 0])
    
    return result # type: ignore

def getLocalQuadData(targetOffs : np.ndarray) -> tuple[launchQuadId, np.ndarray, np.ndarray]:
    """
    Get shooting quadrant info from target position offset

    Args:
        targetOffs (np.ndarray): target position relative to acceleration zone in cannon-local frame

    Returns:
        tuple[launchQuadId, np.ndarray, np.ndarray]: id of quad for UI, position of first charge stack, position of last charge stack
    """
    
    # Tested, adjusted, seems to give correct results.
    
    chargePearlVectors = chargePositions - pearlPosition
    
    # Add target displacement into same array for batch processing
    allVectorArr = np.vstack((chargePearlVectors, -targetOffs))
    chargeAngles = np.arctan2(-allVectorArr[:, 2], allVectorArr[:, 0])
    simpleAnglesDeg = np.mod(np.rad2deg(chargeAngles) + 360, 360)
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

def calculateLaunchParameters(cannonDir : cardinalDir, cannonPos: np.ndarray, targetPos: np.ndarray) -> tuple[launchQuadId, int, int, int, np.ndarray]:
    """
    Calculate launch parameters for the cannon to hit near the target

    Args:
        cannonDir (cardinalDir): cardinal direction taken looking at item frame
        cannonPos (np.ndarray): absolute position of block behind item frame as 1x3 vector
        targetPos (np.ndarray): absolute target position as 1x3 vector

    Returns:
        tuple[launchQuadId, int, int, int, np.ndarray]: launch parameters:
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