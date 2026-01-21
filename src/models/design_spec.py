"""
Pydantic models for architectural design specifications.
These models correspond to the JSON schema defined in config/schemas/design_spec.schema.json
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ZoningType(str, Enum):
    """Zoning classification types."""
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MIXED_USE = "mixed_use"
    INSTITUTIONAL = "institutional"


class StructureType(str, Enum):
    """Building structure types."""
    CONCRETE = "concrete"
    STEEL = "steel"
    WOOD = "wood"
    MIXED = "mixed"


class RoomType(str, Enum):
    """Room functional types."""
    LIVING_ROOM = "living_room"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    DINING_ROOM = "dining_room"
    STUDY = "study"
    STORAGE = "storage"
    HALLWAY = "hallway"
    BALCONY = "balcony"
    UTILITY = "utility"
    ENTRANCE = "entrance"
    PARKING = "parking"
    OTHER = "other"


class DoorType(str, Enum):
    """Door types."""
    SINGLE = "single"
    DOUBLE = "double"
    SLIDING = "sliding"
    FOLDING = "folding"


class WindowType(str, Enum):
    """Window types."""
    FIXED = "fixed"
    CASEMENT = "casement"
    SLIDING = "sliding"
    AWNING = "awning"


class FurnitureType(str, Enum):
    """Furniture types."""
    BED = "bed"
    DESK = "desk"
    CHAIR = "chair"
    SOFA = "sofa"
    TABLE = "table"
    CABINET = "cabinet"
    WARDROBE = "wardrobe"
    REFRIGERATOR = "refrigerator"
    STOVE = "stove"
    SINK = "sink"
    TOILET = "toilet"
    BATHTUB = "bathtub"
    SHOWER = "shower"
    OTHER = "other"


class ProjectInfo(BaseModel):
    """Project metadata and client information."""
    name: str = Field(..., min_length=1, description="Project name")
    client: Optional[str] = Field(None, description="Client name")
    address: Optional[str] = Field(None, description="Project site address")
    architect: Optional[str] = Field(None, description="Lead architect name")
    date: Optional[str] = Field(None, description="Project date (YYYY-MM-DD)")


class Setbacks(BaseModel):
    """Required setbacks in meters."""
    front: Optional[float] = Field(None, ge=0)
    rear: Optional[float] = Field(None, ge=0)
    left: Optional[float] = Field(None, ge=0)
    right: Optional[float] = Field(None, ge=0)


class Site(BaseModel):
    """Site information and constraints."""
    area: Optional[float] = Field(None, ge=0, description="Site area in square meters")
    zoning: Optional[ZoningType] = Field(None, description="Zoning classification")
    max_far: Optional[float] = Field(None, ge=0, le=1000, description="Maximum floor area ratio")
    max_bcr: Optional[float] = Field(None, ge=0, le=100, description="Maximum building coverage ratio")
    setbacks: Optional[Setbacks] = None


class Structure(BaseModel):
    """Structural system information."""
    type: Optional[StructureType] = None
    grid_spacing: Optional[float] = Field(None, description="Column grid spacing in meters")


class Materials(BaseModel):
    """Material specifications."""
    exterior_wall: Optional[str] = None
    interior_wall: Optional[str] = None
    flooring: Optional[str] = None
    roofing: Optional[str] = None


class Polygon(BaseModel):
    """Polygon geometry (GeoJSON-like format)."""
    type: str = Field("Polygon", description="Geometry type")
    coordinates: List[List[float]] = Field(
        ...,
        min_length=3,
        description="Array of [x, y] coordinate pairs forming a closed polygon"
    )

    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v):
        """Validate that each coordinate is a [x, y] pair."""
        for coord in v:
            if len(coord) != 2:
                raise ValueError("Each coordinate must be [x, y] pair")
        return v


class Door(BaseModel):
    """Door specification."""
    wall_index: int = Field(..., ge=0, description="Index of the wall segment where door is placed")
    position: float = Field(..., ge=0, le=1, description="Position along the wall (0.0-1.0)")
    width: float = Field(0.9, ge=0.6, description="Door width in meters")
    height: float = Field(2.1, ge=2.0, description="Door height in meters")
    type: DoorType = Field(DoorType.SINGLE, description="Door type")
    swing_direction: str = Field("inward", description="Swing direction")


class Window(BaseModel):
    """Window specification."""
    wall_index: int = Field(..., ge=0, description="Index of the wall segment where window is placed")
    position: float = Field(..., ge=0, le=1, description="Position along the wall (0.0-1.0)")
    width: float = Field(1.5, ge=0.6, description="Window width in meters")
    height: float = Field(1.2, ge=0.6, description="Window height in meters")
    sill_height: float = Field(0.9, ge=0, description="Window sill height from floor in meters")
    type: WindowType = Field(WindowType.SLIDING, description="Window type")


class Position(BaseModel):
    """2D position with rotation."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    rotation: float = Field(0, ge=0, le=360, description="Rotation angle in degrees")


class Dimensions(BaseModel):
    """3D dimensions."""
    width: Optional[float] = Field(None, ge=0)
    depth: Optional[float] = Field(None, ge=0)
    height: Optional[float] = Field(None, ge=0)


class Furniture(BaseModel):
    """Furniture item specification."""
    type: FurnitureType = Field(..., description="Furniture type")
    position: Position = Field(..., description="Furniture center position")
    dimensions: Optional[Dimensions] = None
    label: Optional[str] = Field(None, description="Custom label")


class RoomMaterials(BaseModel):
    """Room-specific materials."""
    floor: Optional[str] = None
    wall: Optional[str] = None
    ceiling: Optional[str] = None


class Room(BaseModel):
    """Single room specification."""
    name: str = Field(..., min_length=1, description="Room name")
    type: Optional[RoomType] = Field(None, description="Room functional type")
    area: Optional[float] = Field(None, ge=0, description="Room area in square meters")
    geometry: Polygon = Field(..., description="Room boundary polygon")
    doors: Optional[List[Door]] = Field(default_factory=list)
    windows: Optional[List[Window]] = Field(default_factory=list)
    furniture: Optional[List[Furniture]] = Field(default_factory=list)
    materials: Optional[RoomMaterials] = None


class Floor(BaseModel):
    """Single floor specification."""
    level: int = Field(..., description="Floor level (1=ground floor, etc.)")
    height: float = Field(2.8, ge=2.1, description="Floor-to-floor height in meters")
    area: Optional[float] = Field(None, ge=0, description="Total floor area in square meters")
    rooms: List[Room] = Field(..., min_length=1, description="Array of room specifications")


class Building(BaseModel):
    """Building design specification."""
    floors: List[Floor] = Field(..., min_length=1, description="Array of floor specifications")
    structure: Optional[Structure] = None
    materials: Optional[Materials] = None


class DesignSpec(BaseModel):
    """
    Complete architectural design specification.
    This is the Single Source of Truth for all agents.
    """
    project_info: ProjectInfo
    site: Optional[Site] = None
    building: Building

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "project_info": {
                    "name": "3LDK 아파트",
                    "client": "테스트 클라이언트"
                },
                "building": {
                    "floors": [
                        {
                            "level": 1,
                            "rooms": [
                                {
                                    "name": "거실",
                                    "type": "living_room",
                                    "area": 20,
                                    "geometry": {
                                        "type": "Polygon",
                                        "coordinates": [[0, 0], [6, 0], [6, 4], [0, 4], [0, 0]]
                                    },
                                    "doors": [
                                        {"wall_index": 0, "position": 0.5, "width": 0.9}
                                    ],
                                    "windows": [
                                        {"wall_index": 2, "position": 0.5, "width": 1.5}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }
